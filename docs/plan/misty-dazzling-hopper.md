# arXiv論文 著者・引用 自動取得パイプライン — 実装計画

## Context

Neo4j KG v2.1 は Author, AUTHORED_BY, CITES, COAUTHORED_WITH を定義済みだが、論文メタデータの**自動取得パイプラインが存在しない**。手動補完した 236 Author ノード（`auth-*` 形式ID）は再利用不可。

Semantic Scholar API（主）+ arXiv API（副）から著者・引用情報を取得し、既存の graph-queue パイプライン（`emit_graph_queue.py` → `/save-to-graph`）に統合する。

**元プランファイル**: `docs/plan/2026-03-19_arxiv-author-citation-pipeline.md`

---

## 設計判断

| 判断 | 結論 | 理由 |
|------|------|------|
| RateLimiter | `edgar.rate_limiter.RateLimiter` を直接import | 汎用設計、edgar固有ロジックなし。`max_requests_per_second` で S2(1) / arXiv(3) を切り替え |
| エラー階層 | `academic.errors` を新規作成（`news_scraper/exceptions.py` パターン踏襲） | tenacity の retry_if_exception_type に academic 固有の RetryableError が必要 |
| キャッシュ | `market.cache.cache.create_persistent_cache()` を再利用 | TTL=7日, db_path=`data/cache/academic.db` で薄いアダプタのみ作成 |
| 同期/非同期 | sync（httpx.Client）のみ | 35本 × 1 req/sec ≈ 35秒。async は100本超で検討 |
| XML パーサ | feedparser（既存依存） | pyproject.toml に feedparser>=6.0.12 あり。arXiv Atom XML のパースに最適 |
| SCHEMA_VERSION | 1.1 → 2.1 | cites, coauthored_with を relations に追加。既存テスト要修正 |

---

## ファイル構成

```
src/academic/
├── __init__.py              # Public API, __version__="0.1.0"
├── py.typed                 # PEP 561 マーカー
├── types.py                 # PaperMetadata, AuthorInfo, CitationInfo, AcademicConfig
├── errors.py                # AcademicError → RetryableError/PermanentError/RateLimitError/PaperNotFoundError/ParseError
├── retry.py                 # create_retry_decorator(), classify_http_error() — tenacity ラッパー
├── s2_client.py             # S2Client: GET /paper/arXiv:{id}, POST /paper/batch
├── arxiv_client.py          # ArxivClient: GET export.arxiv.org/api/query (feedparser)
├── cache.py                 # get_academic_cache() — market.cache.SQLiteCache アダプタ
├── fetcher.py               # PaperFetcher: cache → S2 → arXiv フォールバック
├── mapper.py                # map_academic_papers() — graph-queue JSON 生成
└── __main__.py              # CLI: python -m academic fetch / backfill

tests/academic/
├── conftest.py
├── unit/
│   ├── test_types.py
│   ├── test_errors.py
│   ├── test_retry.py
│   ├── test_s2_client.py
│   ├── test_arxiv_client.py
│   ├── test_cache.py
│   ├── test_fetcher.py
│   └── test_mapper.py
└── property/
    └── test_mapper_property.py
```

---

## 実装フェーズと Issue 分割

### Wave 0: インフラ更新（1 Issue, 後続すべてをブロック）

**Issue**: `feat(kg): emit_graph_queue schema v2.1 + cites/coauthored_with 追加`

| # | 変更 | ファイル | 行 |
|---|------|---------|-----|
| 1 | `SCHEMA_VERSION = "1.1"` → `"2.1"` | `scripts/emit_graph_queue.py` | L73 |
| 2 | `relations` に `"cites": []`, `"coauthored_with": []` を追加 | `scripts/emit_graph_queue.py` | L176 の後 |
| 3 | テストのアサーション修正（"1.0" → "2.1", relations セットに cites/coauthored_with 追加） | `tests/unit/test_emit_graph_queue.py` | |

**Author ノード移行**（同 Issue またはサブタスク）:
- `scripts/migrate_author_ids.py` 新規作成
- Neo4j から既存 `auth-*` Author ノード取得 → `generate_author_id(name, "academic")` で UUID5 計算 → MERGE + 旧ノード DELETE の Cypher 発行

### Wave 1: パッケージ基盤（1 Issue, Wave 2-3 をブロック）

**Issue**: `feat(academic): パッケージ基盤（types, errors, retry）`

| ファイル | 内容 |
|---------|------|
| `src/academic/__init__.py` | Public API エクスポート, `__version__ = "0.1.0"` |
| `src/academic/py.typed` | PEP 561 マーカー（空ファイル） |
| `src/academic/types.py` | `PaperMetadata`, `AuthorInfo`, `CitationInfo`, `AcademicConfig`（frozen dataclass） |
| `src/academic/errors.py` | `AcademicError` → `RetryableError(status_code, retry_after)` / `PermanentError(status_code)` / `RateLimitError` / `PaperNotFoundError` / `ParseError` |
| `src/academic/retry.py` | `create_retry_decorator(max_attempts=3, base_wait=1.0, max_wait=60.0)`, `classify_http_error()` |
| `pyproject.toml` | packages リストに `"src/academic"` 追加（L129） |
| `tests/academic/` | `conftest.py`, `unit/__init__.py`, `property/__init__.py` |
| テスト | `test_types.py`, `test_errors.py`, `test_retry.py` |

**types.py 主要型定義**:

```python
@dataclass(frozen=True)
class AuthorInfo:
    name: str
    s2_author_id: str | None = None      # Semantic Scholar authorId（将来の名寄せ用）
    organization: str | None = None

@dataclass(frozen=True)
class CitationInfo:
    title: str
    arxiv_id: str | None = None
    s2_paper_id: str | None = None

@dataclass(frozen=True)
class PaperMetadata:
    arxiv_id: str
    title: str
    authors: list[AuthorInfo]
    references: list[CitationInfo]       # この論文が引用している論文
    citations: list[CitationInfo]        # この論文を引用している論文
    published: str | None = None         # ISO 8601
    category: str | None = None          # e.g., "cs.LG"
    abstract: str | None = None
    s2_paper_id: str | None = None

@dataclass(frozen=True)
class AcademicConfig:
    s2_api_key: str | None = None        # S2_API_KEY env var（高レート用）
    s2_rate_limit: int = 1               # req/sec (API key なし: 1, あり: 100)
    arxiv_rate_limit: int = 3            # req/sec
    cache_ttl_seconds: int = 604800      # 7日
    cache_db_path: str = "data/cache/academic.db"
    max_entries: int = 5000
```

### Wave 2: API クライアント（2 Issue, 並列開発可能）

**Issue A**: `feat(academic): Semantic Scholar クライアント`

`s2_client.py`:
- `S2Client.__init__(config)`: httpx.Client, RateLimiter(1 req/sec), retry decorator
- `fetch_paper(arxiv_id) -> dict`: `GET /paper/arXiv:{id}?fields=title,authors,externalIds,references,citations,abstract,publicationDate,fieldsOfStudy`
- `fetch_papers_batch(arxiv_ids) -> list[dict]`: `POST /paper/batch` (最大500件/req で分割)
- 429 → RateLimitError, 404 → PaperNotFoundError, 5xx → RetryableError
- `S2_API_KEY` 環境変数対応（ヘッダー `x-api-key`）

テスト: httpx レスポンスモック（200/404/429/500）、バッチ分割、レート制限

**Issue B**: `feat(academic): arXiv クライアント + キャッシュアダプタ`

`arxiv_client.py`:
- `ArxivClient.__init__(config)`: httpx.Client, RateLimiter(3 req/sec)
- `fetch_paper(arxiv_id) -> PaperMetadata`: `GET http://export.arxiv.org/api/query?id_list={id}`
- feedparser で Atom XML パース: `entry.authors[].name`, `entry.arxiv_primary_category.term`
- references/citations は空リスト（arXiv API は引用情報を提供しない）

`cache.py`:
- `get_academic_cache(config) -> SQLiteCache`: `market.cache.cache.create_persistent_cache()` のラッパー
- `make_cache_key(arxiv_id) -> str`: `"academic:paper:{arxiv_id}"` 形式
- TTL: 7日（604800秒）

テスト: feedparser モック、キャッシュ set/get/miss/TTL

### Wave 3: オーケストレータ + マッパー（2 Issue, 順次）

**Issue A**: `feat(academic): PaperFetcher オーケストレータ`（Wave 2 完了後）

`fetcher.py`:
- `PaperFetcher.__init__(s2_client, arxiv_client, cache, config)`: DI 対応
- `fetch_paper(arxiv_id) -> PaperMetadata`:
  1. キャッシュチェック → ヒットなら即 return
  2. S2Client.fetch_paper() → 成功なら PaperMetadata に変換 + キャッシュ保存
  3. PaperNotFoundError → ArxivClient.fetch_paper() フォールバック（著者のみ）
- `fetch_papers_batch(arxiv_ids) -> list[PaperMetadata]`:
  1. キャッシュ済みとキャッシュなしを分離
  2. 未キャッシュは S2 バッチ取得
  3. S2 で取得できなかったものは arXiv 個別フォールバック
- `_parse_s2_response(raw, arxiv_id) -> PaperMetadata`: S2 レスポンス → 型変換

テスト: キャッシュヒット/ミス、S2 成功/フォールバック、バッチ混合

**Issue B**: `feat(academic): graph-queue マッパー + CLI`（Issue A 完了後）

`mapper.py` — `map_academic_papers(data) -> dict`:
- 入力: `{"papers": [...], "existing_source_ids": [...]}`
- Source ノード: `source_type="paper"`, `publisher="arXiv"`
- Author ノード: `author_type="academic"`, ID は `generate_author_id(name, "academic")`
- AUTHORED_BY: Source → Author
- CITES: `existing_source_ids` に含まれる引用先のみ（スコープ制御）
- COAUTHORED_WITH: 同一論文の著者ペア、`paper_count` / `first_collaboration` 付与

`__main__.py` — CLI:
- `python -m academic fetch --arxiv-id 2303.09406`
- `python -m academic fetch --arxiv-ids 2303.09406 2401.01234`
- 出力: `.tmp/academic/papers.json`

`scripts/emit_graph_queue.py` に登録:
- `COMMAND_MAPPERS["academic-fetch"] = map_academic_papers`

テスト: unit（Source/Author/CITES/COAUTHORED_WITH 生成）+ property（Hypothesis 不変条件3件）

### Wave 4: バックフィル + ドキュメント（1 Issue）

**Issue**: `feat(academic): バックフィル + ドキュメント`

- `backfill` サブコマンド: Neo4j → AUTHORED_BY 未設定論文リスト → batch fetch → graph-queue 出力
- 既存35論文に対してバックフィル実行
- `CLAUDE.md` パッケージ一覧に `academic` 追加

---

## 再利用する既存コード

| モジュール | 関数/クラス | 用途 |
|-----------|------------|------|
| `src/database/id_generator.py` | `generate_source_id(url)` | Source ノード ID |
| `src/database/id_generator.py` | `generate_author_id(name, type)` | Author ノード ID (UUID5) |
| `src/edgar/rate_limiter.py` | `RateLimiter(max_requests_per_second)` | API レート制限 |
| `src/market/cache/cache.py` | `create_persistent_cache(db_path, ttl, max_entries)` | SQLite キャッシュ |
| `scripts/emit_graph_queue.py` | `_empty_queue(cmd, path)` | graph-queue 基盤構造 |

---

## 依存関係グラフ

```
Wave 0 (emit_graph_queue 更新 + Author移行)
  │
Wave 1 (types, errors, retry, パッケージ基盤)
  │
  ├── Wave 2A (S2Client)──┐
  │                        ├── Wave 3A (PaperFetcher)
  └── Wave 2B (ArxivClient + Cache)──┘
                                         │
                                    Wave 3B (Mapper + CLI + emit_graph_queue 登録)
                                         │
                                    Wave 4 (Backfill + Docs)
```

Wave 2A と 2B は並列開発可能。

---

## 検証方法

1. **ユニットテスト**: `uv run pytest tests/academic/ -v`
2. **品質チェック**: `make check-all`
3. **統合テスト（手動）**:
   ```bash
   # S2 API から取得
   python -m academic fetch --arxiv-id 2303.09406
   # graph-queue 生成
   uv run python scripts/emit_graph_queue.py --command academic-fetch --input .tmp/academic/papers.json
   # Neo4j 投入
   /save-to-graph
   ```
4. **Neo4j 確認**:
   ```cypher
   MATCH (s:Source {source_type: 'paper'})-[:AUTHORED_BY]->(a:Author)
   RETURN s.title, collect(a.name) AS authors LIMIT 5
   ```

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| S2 API ダウン | arXiv フォールバック（著者のみ取得、引用なし） |
| 著者名の揺らぎ（"S. Wang" vs "Saizhuo Wang"） | 初期はname-based UUID5。将来 S2 authorId で名寄せ |
| feedparser で `<arxiv:affiliation>` 未パース | feedparser の namespace 辞書を確認、必要なら xml.etree fallback |
| market.cache.cache の pandas 依存 | pandas は既存プロジェクト依存。問題なし |
| 既存テスト schema_version 不整合（"1.0" vs "1.1"） | Wave 0 で "2.1" に統一しテスト修正 |
