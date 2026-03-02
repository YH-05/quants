# Plan: Gemini Embedding API 統合 — テキストベクトル化パイプライン

## Context

`src/embedding/` パッケージはニュース記事を ChromaDB に格納するパイプラインとして実装済みだが、埋め込みベクトルはダミー（`np.zeros(768)`）を使用しており、実際の embedding モデルは未統合。

**目的**: Gemini Embedding API (`gemini-embedding-001`) を統合し、テキストを実ベクトル（3072次元）に変換する機能を実装する。クオンツ分析向けに、銘柄×テキスト紐付け・クロスセクション銘柄グルーピング・時系列変化の分析基盤を構築する。

**ユーザー要件**:
- 次元数: 3072（最大品質）
- 対象: 既存記事（バッチ）+ 今後の収集パイプライン統合
- DB設計: テキスト+銘柄+ベクトルを同じコレクション管理、**モデルごとにコレクションを分離**
- 統合方式: 自前で Gemini API 呼び出し → `collection.add(embeddings=...)` で格納

---

## Gemini Embedding API 仕様（調査結果）

| 項目 | 値 |
|------|-----|
| モデル | `gemini-embedding-001` (GA) |
| SDK | `google-genai` (`pip install google-genai`) |
| API | `client.models.embed_content(model=..., contents=[...], config=EmbedContentConfig(...))` |
| 次元数 | 128〜3072（MRL技術、デフォルト3072） |
| 入力制限 | 2048 tokens/テキスト |
| task_type | CLUSTERING / RETRIEVAL_DOCUMENT / SEMANTIC_SIMILARITY 等8種 |
| レート | Free: 100 RPM, 250K TPM / Paid Tier1: 150-300 RPM |
| 料金 | Free: 無料 / Standard: $0.15/1M tokens / Batch: $0.075/1M tokens |

---

## 現状と Gap

| 項目 | 現在 | ゴール |
|------|------|--------|
| ベクトル | `np.zeros(768)` ダミー | Gemini API で 3072次元の実ベクトル |
| has_embedding | 常に `"false"` | 実ベクトル生成時に `"true"` に更新 |
| google-genai | 未導入 | optional dependency として追加 |
| API キー | 未設定 | `GOOGLE_API_KEY` 環境変数管理 |
| 後付け処理 | なし | `has_embedding=false` の既存記事をバッチ更新 |
| エクスポート | なし | numpy / DataFrame / Parquet でクオンツ分析に接続 |
| CLI | 単一コマンド | サブコマンド（ingest / embed / backfill / export） |

---

## 実装計画

### 新規ファイル

| ファイル | 役割 |
|---------|------|
| `src/embedding/embedder.py` | Gemini API 呼び出し（バッチ処理・レート制御・リトライ） |
| `src/embedding/export.py` | クオンツ分析向けエクスポート（numpy / DataFrame / Parquet） |
| `tests/embedding/unit/test_embedder.py` | embedder 単体テスト（API モック） |
| `tests/embedding/unit/test_export.py` | export 単体テスト |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/embedding/types.py` | `PipelineConfig` に embedding フィールド追加、`EmbeddingResult` 型追加 |
| `src/embedding/chromadb_store.py` | `store_articles()` に `embeddings` 引数追加、`update_embeddings()` / `get_unembedded_articles()` 新規追加 |
| `src/embedding/pipeline.py` | Step 3.5（embedding）追加、`backfill_embeddings()` 新規追加 |
| `src/embedding/cli.py` | サブコマンド化（ingest / embed / backfill / export） |
| `src/embedding/__init__.py` | 新規エクスポート追加 |
| `pyproject.toml` | `google-genai` を optional dependency `gemini` グループに追加 |
| `src/utils_core/settings.py` | `get_google_api_key()` 追加 |
| `tests/embedding/conftest.py` | embedding 関連フィクスチャ追加 |

---

### 1. `embedder.py` — Gemini API クライアント

```python
class GeminiEmbedder:
    def __init__(
        self,
        *,
        api_key: str | None = None,         # None → 環境変数 GOOGLE_API_KEY
        model: str = "gemini-embedding-001",
        output_dimensionality: int = 3072,
        task_type: str = "CLUSTERING",       # 銘柄グルーピングがメイン用途
    ) -> None: ...

    async def embed_texts(
        self,
        texts: list[str],
        *,
        batch_size: int = 20,       # 1 API call あたりのテキスト数
        max_concurrent: int = 5,    # 並行バッチ数
        delay: float = 0.6,         # Free 100RPM 対応
        max_retries: int = 3,       # 指数バックオフ
    ) -> list[list[float]]: ...

    async def _embed_batch(self, texts: list[str], *, max_retries: int) -> list[list[float]]: ...
    def _truncate_text(self, text: str, max_tokens: int = 2048) -> str: ...  # tiktoken で推定
```

- `google-genai` は optional import（`chromadb_store.py` と同じパターン）
- `tenacity` で指数バックオフリトライ（429/500/503のみ）
- `tiktoken`（既存依存）でトークン数推定・トランケーション
- 既存 `rate_limiter.py` の `RateLimiter` を再利用

### 2. `types.py` — PipelineConfig 拡張

```python
@dataclass
class PipelineConfig:
    # ... 既存フィールド（変更なし）...

    # Embedding 設定（新規追加）
    enable_embedding: bool = False       # デフォルト False → 既存テスト影響ゼロ
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 3072
    embedding_task_type: str = "CLUSTERING"
    embedding_batch_size: int = 20
    embedding_max_concurrent: int = 5
    embedding_delay: float = 0.6
    embedding_max_retries: int = 3
    google_api_key: str | None = None

@dataclass
class EmbeddingResult:
    url: str
    embedding: list[float]
    model: str
    task_type: str
    created_at: str
```

### 3. `chromadb_store.py` — 実ベクトル対応

**`store_articles()` 拡張** — キーワード引数 `embeddings` 追加（後方互換）:
```python
def store_articles(
    ...,
    embeddings: list[list[float]] | None = None,  # None → ダミーベクトル
) -> int:
```

**`_build_metadata()` 拡張** — `has_embedding` を動的に:
```python
def _build_metadata(
    ...,
    *,
    has_embedding: bool = False,
    embedding_model: str = "",
    embedded_at: str = "",
) -> dict[str, str]:
```

**新規関数**:
- `get_unembedded_articles()` → `has_embedding=false` の記事 ID + ドキュメントを返す
- `update_embeddings()` → 既存記事のベクトル更新 + メタデータ `has_embedding=true` に変更

### 4. `pipeline.py` — embedding ステップ統合

```
run_pipeline() フロー:
  Step 1: read_all_news_json()
  Step 2: get_existing_ids() → 新規フィルタ
  Step 3: extract_contents()
  Step 3.5: GeminiEmbedder.embed_texts()  ← NEW（enable_embedding=True 時のみ）
  Step 4: store_articles(embeddings=実ベクトル or None)
```

**新規関数**: `backfill_embeddings(config)` — 既存ダミーベクトルを実ベクトルに後付け更新

### 5. `export.py` — クオンツ分析向けエクスポート

```python
def get_embedding_matrix(chromadb_path, collection_name, *, tickers=None, only_embedded=True
) -> tuple[np.ndarray, pd.DataFrame]:
    """(N×3072 ベクトル行列, N行メタデータ DataFrame) を返す"""

def get_ticker_centroid(chromadb_path, collection_name, ticker) -> np.ndarray:
    """銘柄のセントロイド（平均ベクトル）→ クロスセクション比較用"""

def export_similarity_matrix(chromadb_path, collection_name, *, tickers=None, metric="cosine"
) -> pd.DataFrame:
    """銘柄×銘柄のコサイン類似度行列 → グルーピング分析用"""

def export_to_parquet(chromadb_path, collection_name, output_path, *, tickers=None
) -> int:
    """Parquet 出力 → 外部クオンツパイプライン連携用"""
```

### 6. `cli.py` — サブコマンド化

```
embedding-pipeline ingest     # 既存フロー（ダミーベクトル）— 後方互換
embedding-pipeline embed      # ingest + Gemini 実ベクトル生成
embedding-pipeline backfill   # 既存ダミーベクトルを実ベクトルに後付け更新
embedding-pipeline export     # ChromaDB → numpy/CSV/Parquet エクスポート
```

サブコマンドなしの場合は `ingest` として動作（後方互換）。

### 7. DB 分離設計

コレクション名 = モデル名の既存設計をそのまま活用:
```
data/chromadb/
  collection: "gemini-embedding-001"        # 3072次元
  collection: "text-embedding-004"          # 将来の別モデル
```

CLI の `--collection-name` でコレクション切替。

---

## Wave 分割

### Wave 1: 基盤（並行可能）

| # | タスク | ファイル |
|---|--------|---------|
| 1-1 | `google-genai` optional dependency 追加 | `pyproject.toml` |
| 1-2 | `EmbeddingResult` 型追加 + `PipelineConfig` フィールド追加 | `types.py` |
| 1-3 | `get_google_api_key()` 関数追加 | `utils_core/settings.py` |

### Wave 2: コアモジュール（Wave 1 後、2-1 と 2-2 は並行可能）

| # | タスク | ファイル |
|---|--------|---------|
| 2-1 | `GeminiEmbedder` 実装 + テスト | `embedder.py`, `test_embedder.py` |
| 2-2 | `store_articles()` 拡張 + `update_embeddings()` + `get_unembedded_articles()` + テスト更新 | `chromadb_store.py`, `test_chromadb_store.py` |

### Wave 3: パイプライン統合（Wave 2 後、3-1 と 3-2 は並行可能）

| # | タスク | ファイル |
|---|--------|---------|
| 3-1 | Step 3.5 追加 + `backfill_embeddings()` + テスト更新 | `pipeline.py`, `test_pipeline.py` |
| 3-2 | エクスポート機能 + テスト | `export.py`, `test_export.py` |

### Wave 4: CLI 統合（Wave 3 後）

| # | タスク | ファイル |
|---|--------|---------|
| 4-1 | サブコマンド化 + エクスポート更新 | `cli.py`, `__init__.py` |

### Wave 5: 品質保証

| # | タスク |
|---|--------|
| 5-1 | `make check-all` 全パス確認 |
| 5-2 | 既存テスト64件の回帰確認 |
| 5-3 | 小規模データで Gemini API 実呼び出し E2E テスト |

---

## 後方互換性の保証

| 変更 | 既存テストへの影響 |
|------|------------------|
| `PipelineConfig` フィールド追加 | 全て新規フィールドにデフォルト値あり → **影響なし** |
| `store_articles()` に `embeddings` 引数追加 | `None` デフォルト → **影響なし** |
| `_build_metadata()` に `has_embedding` 引数追加 | `False` デフォルト → **影響なし** |
| `enable_embedding` デフォルト `False` | 既存フローは全てダミーベクトル維持 → **影響なし** |
| CLI サブコマンド化 | サブコマンドなし = `ingest` → **影響なし** |

---

## 検証方法

1. **ユニットテスト**: `uv run pytest tests/embedding/ -v` — 既存64件 + 新規テスト全 PASS
2. **型チェック**: `uv run pyright src/embedding/` — エラーなし
3. **品質チェック**: `make check-all` — 全パス
4. **E2E テスト（手動）**:
   ```bash
   # 1. 小規模 ingest（ダミーベクトル、従来動作確認）
   uv run embedding-pipeline ingest --news-dir data/raw/news --sources cnbc

   # 2. 実ベクトル生成
   uv run embedding-pipeline embed --news-dir data/raw/news --sources cnbc

   # 3. 後付け更新
   uv run embedding-pipeline backfill --limit 10

   # 4. エクスポート確認
   uv run embedding-pipeline export --format parquet --output data/exports/embeddings.parquet
   ```

---

## 再利用する既存リソース

| リソース | パス | 用途 |
|---------|------|------|
| optional import パターン | `src/embedding/chromadb_store.py` L26-30 | `google-genai` の optional guard |
| API キー管理 | `src/utils_core/settings.py` `get_fred_api_key()` | `get_google_api_key()` の実装参考 |
| 非同期レート制御 | `src/embedding/rate_limiter.py` | `GeminiEmbedder` でそのまま再利用 |
| tiktoken | `pyproject.toml` L45 `tiktoken>=0.7.0` | テキストトランケーション |
| tenacity | `pyproject.toml` L25 `tenacity>=9.1.2` | 指数バックオフリトライ |
| バッチ処理パターン | `src/embedding/chromadb_store.py` L237-249 | `_BATCH_SIZE` ループ |
