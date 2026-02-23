# Quants → Finance 4コンポーネント移植計画

## Context

Quants プロジェクトには Finance に欠けている実装が複数存在する。本計画では以下4つを Finance に移植し、コードベースを統合する:

1. **DuckDB upsert ロジック** - DataFrame→テーブル保存（replace/append/upsert）
2. **Configuration パターン** - frozen dataclass による一括環境変数バリデーション
3. **Bloomberg ラッパー強化** - プレースホルダ実装を実際の BLPAPI レスポンス処理で置換
4. **News Embedding パイプライン** - 記事→ベクトルDB(ChromaDB)格納パイプライン

## 実装順序

依存関係と複雑度を考慮し、以下の順で実施:

```
Phase 1: DuckDB upsert (低複雑度・自己完結)
Phase 2: ProjectConfig (低複雑度・基盤)
Phase 3: Bloomberg 強化 (高複雑度・既存コード修正)
Phase 4: News Embedding (中-高複雑度・新パッケージ)
```

---

## Phase 1: DuckDB Upsert ロジック

### 目的
`DuckDBClient` に DataFrame→テーブル保存機能（3モード: replace/append/upsert）を追加する。

### 移植元
- `/Users/yukihata/Desktop/Quants/src/database/duckdb_utils.py` (~133行)

### 変更ファイル

| ファイル | 操作 | 内容 |
|---------|------|------|
| `src/database/db/duckdb_client.py` | **修正** | `store_df()`, `get_table_names()` メソッド追加 |
| `src/database/db/__init__.py` | **修正** | エクスポート追加 |
| `src/database/__init__.py` | **修正** | エクスポート追加 |
| `tests/database/db/unit/test_duckdb_client.py` | **修正** | テストクラス追加 |
| `tests/database/db/property/test_duckdb_upsert_property.py` | **新規** | プロパティテスト |

### 追加メソッド

```python
# DuckDBClient に追加
def store_df(
    self,
    df: pd.DataFrame,
    table_name: str,
    *,
    key_columns: list[str] | None = None,
    if_exists: Literal["replace", "append", "upsert"] = "upsert",
) -> int:
    """Store DataFrame to DuckDB table with dedup support."""

def get_table_names(self) -> list[str]:
    """Get list of table names in the database."""
```

### upsert ロジック（Quants から移植）

- **replace**: `IS NOT DISTINCT FROM` で全カラム一致行を除外して INSERT
- **append**: 重複チェックなしで直接 INSERT
- **upsert**: `key_columns` 一致行を DELETE → 全新規行を INSERT

### テストケース

- `test_正常系_新規テーブルにDataFrameを保存`
- `test_正常系_upsertでキーカラム重複行が更新される`
- `test_正常系_replaceで全カラム一致行がスキップされる`
- `test_正常系_appendで重複チェックなしに追記される`
- `test_異常系_upsertでkey_columnsがNoneだとValueError`
- `test_異常系_空のDataFrameで何もしない`
- プロパティテスト: `upsert後のkey_columns値がユニーク`

### 依存追加
なし（duckdb, pandas は既存）

---

## Phase 2: ProjectConfig (Configuration パターン)

### 目的
frozen dataclass `ProjectConfig` を追加し、環境変数の一括バリデーション（fail-fast）を実現する。既存の lazy getter 関数は後方互換のため維持。

### 移植元
- `/Users/yukihata/Desktop/Quants/src/configuration/settings.py`

### 変更ファイル

| ファイル | 操作 | 内容 |
|---------|------|------|
| `src/utils_core/config.py` | **新規** | `ProjectConfig` frozen dataclass |
| `src/utils_core/__init__.py` | **修正** | `ProjectConfig` エクスポート追加 |
| `tests/utils_core/unit/test_config.py` | **新規** | 単体テスト |

### ProjectConfig 設計

```python
@dataclass(frozen=True)
class ProjectConfig:
    fred_api_key: str
    log_level: str = "INFO"
    log_format: str = "console"
    log_dir: str = "logs/"
    project_env: str = "development"

    @classmethod
    def from_env(cls, *, env_path: Path | None = None) -> "ProjectConfig":
        """Load from environment variables. Validates ALL required vars upfront."""

    @classmethod
    def from_defaults(cls, **overrides: str) -> "ProjectConfig":
        """Create with defaults (for testing)."""
```

### 設計ポイント

- `from_env()` は `_find_env_file()` を再利用（`settings.py` から import）
- 欠落している必須変数を全て収集してから `ValueError` を発生（Quants パターン）
- 既存 `get_fred_api_key()` 等は変更なし（後方互換）

### テストケース

- `test_正常系_from_envで全環境変数がロードされる`
- `test_正常系_from_defaultsでデフォルト値が設定される`
- `test_異常系_必須環境変数が欠けているとValueError`
- `test_正常系_frozen_dataclassで変更不可`

### 依存追加
なし

---

## Phase 3: Bloomberg ラッパー強化

### 目的
`BloombergFetcher` のプレースホルダメソッド（`_process_*` が空 DataFrame/リストを返す）を、Quants の実際の BLPAPI レスポンス処理ロジックで置換する。チャンキング・増分更新も追加。

### 移植元
- `/Users/yukihata/Desktop/Quants/src/bloomberg/data_blpapi.py` (~1777行)

### 変更ファイル

| ファイル | 操作 | 内容 |
|---------|------|------|
| `src/market/bloomberg/fetcher.py` | **修正** | 6つの `_process_*` メソッド実装、3つの新規メソッド |
| `src/market/bloomberg/types.py` | **修正** | `ChunkConfig`, `EarningsInfo`, `IdentifierConversionResult` 追加 |
| `src/market/bloomberg/constants.py` | **修正** | `DEFAULT_CHUNK_SIZE` 等の定数追加 |
| `src/market/bloomberg/__init__.py` | **修正** | 新型のエクスポート追加 |
| `tests/market/unit/bloomberg/test_response_processing.py` | **新規** | レスポンス処理テスト |
| `tests/market/unit/bloomberg/conftest.py` | **修正** | mock Element factory 追加 |

### 実装するメソッド

**プレースホルダ置換（既存メソッドの中身を実装）:**

1. `_process_historical_response()` - BLPAPI HistoricalDataRequest のレスポンス解析
2. `_process_reference_response()` - BLPAPI ReferenceDataRequest のレスポンス解析
3. `_process_id_conversion()` - 識別子変換レスポンス解析
4. `_process_news_response()` - ニュースレスポンス解析
5. `_process_index_members()` - インデックス構成銘柄レスポンス解析
6. `_process_field_info()` - フィールド情報レスポンス解析

**新規メソッド:**

7. `get_financial_data_chunked()` - チャンキング対応版（chunk_size=50, max_retries=3）
8. `get_earnings_dates()` - 決算日取得
9. `convert_identifiers_with_date()` - 基準日指定の識別子変換
10. `update_historical_data()` - DBからの増分更新

### 変換ルール（Quants → Finance）

| Quants | Finance |
|--------|---------|
| `print("...")` | `logger.error("...", security=security)` (structlog) |
| `return pd.DataFrame()` on error | `raise BloombergDataError(...)` |
| `id_type: str` | `IDType` enum |
| `verbose: bool` | structlog のログレベルで制御 |

### テスト方針

- BLPAPI `Element` オブジェクトの mock factory を conftest.py に作成
- `hasElement()`, `getElement()`, `getValue()`, `numValues()`, `values()` をシミュレート
- 全テストは blpapi がインストールされていなくても実行可能（完全 mock）

### 注意: pyproject.toml の `norecursedirs`

現在 `tests/market/unit/bloomberg` が除外されている。テスト完成後に除外設定を削除する:

```toml
# 削除対象
norecursedirs = ["tests/skills/finance_news_workflow/unit", "tests/market/unit/bloomberg"]
# ↓
norecursedirs = ["tests/skills/finance_news_workflow/unit"]
```

### 依存追加
なし（blpapi は任意・既存パターンで `# type: ignore[import-not-found]`）

---

## Phase 4: News Embedding パイプライン

### 目的
新パッケージ `src/embedding/` を作成し、ニュース記事をChromaDBに格納するパイプラインを構築する。

### 移植元
- `/Users/yukihata/Desktop/Quants/src/news_embedding/` (8ファイル)

### 変更ファイル

| ファイル | 操作 | 内容 |
|---------|------|------|
| `src/embedding/__init__.py` | **新規** | パッケージ定義・エクスポート |
| `src/embedding/types.py` | **新規** | `ArticleRecord`, `PipelineConfig`, `ExtractionResult` |
| `src/embedding/reader.py` | **新規** | JSON読み込み・URL重複排除 |
| `src/embedding/rate_limiter.py` | **新規** | 自己完結型 asyncio RateLimiter |
| `src/embedding/extractor.py` | **新規** | 非同期コンテンツ抽出（trafilatura + playwright fallback） |
| `src/embedding/chromadb_store.py` | **新規** | ChromaDB CRUD（SHA-256 ID、バッチ保存） |
| `src/embedding/pipeline.py` | **新規** | パイプライン統合（reader→extractor→store） |
| `src/embedding/cli.py` | **新規** | CLI エントリポイント |
| `src/embedding/__main__.py` | **新規** | `python -m embedding` 対応 |
| `pyproject.toml` | **修正** | chromadb optional dep, packages リスト, scripts |
| `tests/embedding/unit/test_*.py` | **新規** | 各モジュールの単体テスト (6ファイル) |
| `tests/embedding/conftest.py` | **新規** | 共通フィクスチャ |

### パイプラインフロー

```
read_all_news_json()     → list[ArticleRecord]
  ↓
deduplicate_by_url()     → list[ArticleRecord] (URL重複排除)
  ↓
get_existing_ids()       → set[str] (ChromaDB既存ID取得)
  ↓
_filter_new_articles()   → list[ArticleRecord] (差分のみ)
  ↓
extract_contents()       → list[ExtractionResult] (async, rate limited)
  ↓
store_articles()         → int (ChromaDBに格納、バッチ100件)
```

### Quants 依存の解消

Quants の `news_scraper.async_core.RateLimiter` を直接使わず、`embedding/rate_limiter.py` に自己完結実装（~50行の asyncio.Semaphore ラッパー）を作成。

### ChromaDB ガード

```python
try:
    import chromadb
except ImportError:
    chromadb = None  # type: ignore[assignment]

def _ensure_chromadb() -> None:
    if chromadb is None:
        raise ImportError(
            "chromadb is required. Install with: uv pip install 'finance[chromadb]'"
        )
```

### pyproject.toml 変更

```toml
# optional-dependencies に追加
chromadb = ["chromadb>=0.5.0"]

# packages に追加
packages = [..., "src/embedding"]

# scripts に追加
news-embedding = "embedding.cli:main"
```

### テストケース（主要なもの）

- `test_reader.py`: JSON読み込み、ソースフィルタ、重複排除、不正JSONスキップ
- `test_rate_limiter.py`: 同時実行数制限、delay制御
- `test_extractor.py`: trafilatura成功、playwright fallback、両方失敗
- `test_chromadb_store.py`: SHA-256 ID生成の決定性、バッチ分割、既存IDスキップ
- `test_pipeline.py`: 全ステップ実行、記事0件で早期終了

### 依存追加

```toml
chromadb = ["chromadb>=0.5.0"]  # optional
```

---

## 検証戦略

### 各 Phase 完了時

```bash
make check-all  # ruff format + lint + pyright + pytest
```

### 全 Phase 完了後

```bash
make test-cov   # カバレッジ80%以上を確認
```

### 後方互換性確認

- 既存テスト（`tests/database/`, `tests/market/`, `tests/utils_core/`）が全て PASS
- 既存の `DuckDBClient` API に破壊的変更なし
- 既存の `get_fred_api_key()` 等の getter 関数が変更なし
- `BloombergFetcher` の公開メソッドシグネチャが変更なし

---

## リスク評価

| Phase | リスク | 対策 |
|-------|--------|------|
| 1: DuckDB | 低 - 純粋な追加 | テーブル名・カラム名のSQLインジェクション検証を追加 |
| 2: Config | 低 - 純粋な追加 | `load_project_env()` の二重読み込み回避 |
| 3: Bloomberg | 高 - 既存コード修正 | mock factory で BLPAPI Element を完全シミュレート |
| 4: Embedding | 中 - 新パッケージ | chromadb を optional で隔離、RateLimiter を自己完結化 |
