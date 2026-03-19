# arXiv論文 著者・引用 自動取得パイプライン

## Context

Neo4j KGスキーマv2.1はAuthor, AUTHORED_BY, CITES, COAUTHORED_WITHを定義済みだが、論文メタデータの**自動取得パイプラインが存在しない**。今回の手動補完（236 Author, 226 AUTHORED_BY, 4 CITES, 953 COAUTHORED_WITH）はサブエージェントによる一回限りの作業で、今後の論文追加時に再利用できない。

arXiv API / Semantic Scholar API から著者・引用情報を構造化データとして取得し、既存のgraph-queueパイプライン（emit_graph_queue.py → save-to-graph）に統合する。

## 設計判断

### API選択: Semantic Scholar を主、arXiv をフォールバック

| API | 著者 | 所属 | 引用(references) | 被引用(citations) | レート制限 |
|-----|:----:|:----:|:----------------:|:-----------------:|:---------:|
| arXiv API | o | o | x | x | 3 req/sec |
| Semantic Scholar API | o | △（一部のみ） | o | o | 1 req/sec |

→ S2で著者+引用を一括取得。S2に未登録の場合のみarXiv APIにフォールバック。

### ID形式: UUID5に統一（既存auth-*ノードは移行）

既存のAuthor 236ノードは手動補完時に `auth-{lastname}-{firstname}` 形式で作成されたが、`generate_author_id()` はUUID5形式を返す。**graph-queueパイプラインとの一貫性のためUUID5に統一**し、既存ノードはPhase 0で移行する。

### パッケージ配置: `src/academic/`（新規パッケージ）

他パッケージと同様にドメイン単位で分離。`market`（yfinance/FRED）、`edgar`（SEC）と並ぶ学術データソースパッケージ。

---

## ファイル構成

```
src/academic/
├── __init__.py              # Public API
├── py.typed
├── types.py                 # PaperMetadata, AuthorInfo, CitationInfo
├── errors.py                # AcademicError, RateLimitError, PaperNotFoundError
├── s2_client.py             # Semantic Scholar API クライアント（httpx）
├── arxiv_client.py          # arXiv Atom API クライアント（httpx、フォールバック用）
├── fetcher.py               # オーケストレータ（S2→arXivフォールバック、キャッシュ）
├── cache.py                 # SQLiteCache アダプタ（TTL 7日）
└── mapper.py                # map_papers(): PaperMetadata → graph-queue JSON

tests/academic/
├── conftest.py
├── unit/
│   ├── test_s2_client.py
│   ├── test_arxiv_client.py
│   ├── test_fetcher.py
│   ├── test_mapper.py
│   └── test_errors.py
└── property/
    └── test_mapper_property.py
```

## データフロー

```
python -m academic fetch --arxiv-id 2303.09406
    │
    ▼
PaperFetcher.fetch_paper()
    ├── SQLiteCache hit? → return cached
    ├── S2Client.fetch_paper("2303.09406")
    │     ├── 200: authors + references + citations
    │     ├── 404: → ArxivClient fallback (authors only)
    │     └── 429/5xx: retry with backoff
    └── SQLiteCache.set()
    │
    ▼
PaperMetadata
    │
    ▼
emit_graph_queue.py --command academic-fetch --input .tmp/academic/papers.json
    │
    ▼
.tmp/graph-queue/academic-fetch/gq-{ts}-{rand}.json
    │
    ▼
/save-to-graph  →  Neo4j (Source, Author, AUTHORED_BY, CITES, COAUTHORED_WITH)
```

## 実装フェーズ

### Phase 0: 既存Authorノード移行 + emit_graph_queue更新

**目的**: graph-queueパイプラインをv2.1対応にし、既存データとの整合性を確保

1. **emit_graph_queue.py 更新**
   - `SCHEMA_VERSION` を `"1.1"` → `"2.1"` に変更
   - `_empty_queue()` の `relations` に `"cites": []`, `"coauthored_with": []` を追加
   - `COMMAND_MAPPERS` に `"academic-fetch": map_papers` を追加（Phase 2で実装後）

2. **既存Authorノードのid移行**（Neo4j Cypherで一括実行）
   - 既存 `auth-*` 形式のAuthorノード → UUID5形式の新ノードに移行
   - 関連リレーション（AUTHORED_BY, COAUTHORED_WITH）も付け替え
   - 旧ノードを削除

**対象ファイル**:
- `scripts/emit_graph_queue.py` (L73, L155-177)

### Phase 1: パッケージ基盤

**目的**: types, errors, パッケージ構造の確立

1. `src/academic/` ディレクトリ作成
2. `types.py`: `PaperMetadata`, `AuthorInfo`, `CitationInfo`, `AcademicConfig` (frozen dataclass)
3. `errors.py`: `AcademicError` → `RetryableError` / `PermanentError` / `RateLimitError` / `PaperNotFoundError`
4. `pyproject.toml` にパッケージ登録
5. `tests/academic/` 構造作成

**参照パターン**:
- `src/news_scraper/errors.py` (エラー階層)
- `src/database/id_generator.py` (ID生成)

### Phase 2: Semantic Scholar クライアント

**目的**: 主データソース（著者+引用）の実装

1. `s2_client.py`:
   - `S2Client` クラス（httpx.Client ベース）
   - `fetch_paper(arxiv_id) -> dict`: `GET /paper/arXiv:{id}?fields=title,authors,references,externalIds`
   - `fetch_papers_batch(arxiv_ids) -> list[dict]`: `POST /paper/batch` (最大500件/リクエスト)
   - レート制限: `src/edgar/rate_limiter.py` パターン踏襲（1 req/sec）
   - リトライ: `src/news_scraper/retry.py` パターン踏襲（tenacity, 指数バックオフ+jitter）
   - 429 → `RateLimitError`, 404 → `PaperNotFoundError`, 5xx → `RetryableError`
2. `tests/academic/unit/test_s2_client.py`: httpxレスポンスモック

**参照パターン**:
- `src/edgar/rate_limiter.py` (トークンバケット)
- `src/news_scraper/retry.py` (tenacity デコレータ)

### Phase 3: arXiv クライアント + キャッシュ

**目的**: フォールバック（著者のみ）+ APIレスポンスキャッシュ

1. `arxiv_client.py`:
   - `ArxivClient` クラス
   - `fetch_paper(arxiv_id) -> PaperMetadata`: `GET http://export.arxiv.org/api/query?id_list={id}`
   - Atom XML パース（feedparser or xml.etree）: `<author><name>`, `<arxiv:affiliation>`
   - レート制限: 3 req/sec
2. `cache.py`:
   - `get_academic_cache() -> SQLiteCache` (データベースパス: `data/cache/academic.db`)
   - TTL: 7日（604800秒）
   - キーフォーマット: `academic:paper:{arxiv_id}`
3. `fetcher.py`:
   - `PaperFetcher` クラス（S2 + arXiv + cache のオーケストレータ）
   - `fetch_paper(arxiv_id) -> PaperMetadata`: キャッシュ → S2 → arXiv fallback
   - `fetch_papers_batch(arxiv_ids) -> list[PaperMetadata]`
4. テスト

**参照パターン**:
- `src/market/cache/cache.py` (SQLiteCache)

### Phase 4: graph-queue マッパー + CLI

**目的**: graph-queueパイプラインとの統合、CLIインターフェース

1. `mapper.py`:
   - `map_papers(data) -> dict`: PaperMetadataリスト → graph-queue JSON
   - Source(source_type='paper') ノード生成
   - Author(author_type='academic') ノード生成（`generate_author_id()` でUUID5 ID）
   - AUTHORED_BY, CITES, COAUTHORED_WITH リレーション生成
   - **CITES は `existing_source_ids` に含まれるarXiv IDのみ**（DB内論文同士）
2. `__init__.py`, `__main__.py`, CLI:
   - `python -m academic fetch --arxiv-id 2303.09406`
   - `python -m academic fetch --arxiv-ids 2303.09406 2401.01234`
   - `python -m academic backfill` (Neo4jのAUTHORED_BY未設定論文を一括取得)
3. `emit_graph_queue.py` に `map_papers` を登録
4. テスト（unit + property）

### Phase 5: バックフィル実行 + ドキュメント

**目的**: 既存35論文のデータ補完、ドキュメント整備

1. `backfill` サブコマンド実装（Neo4j → 対象論文リスト → batch fetch → graph-queue出力）
2. 既存35論文に対してバックフィル実行
3. CLAUDE.md パッケージ一覧に `academic` を追加
4. `src/academic/README.md` 作成

---

## graph-queue JSON フォーマット（mapper出力例）

```json
{
  "schema_version": "2.1",
  "queue_id": "gq-20260319120000-a1b2c3d4",
  "command_source": "academic-fetch",
  "sources": [
    {
      "id": "<UUID5 from https://arxiv.org/abs/2303.09406>",
      "url": "https://arxiv.org/abs/2303.09406",
      "title": "Full-State Graph Convolutional LSTM...",
      "source_type": "paper",
      "publisher": "arXiv",
      "published": "2023-03-16T...",
      "category": "cs.LG"
    }
  ],
  "authors": [
    {
      "id": "<UUID5 from author:Author Name:academic>",
      "name": "Author Name",
      "author_type": "academic",
      "organization": "MIT"
    }
  ],
  "relations": {
    "authored_by": [
      {"from_id": "<source_id>", "to_id": "<author_id>"}
    ],
    "cites": [
      {"from_id": "<this_source_id>", "to_id": "<cited_source_id>"}
    ],
    "coauthored_with": [
      {"from_id": "<author_id_1>", "to_id": "<author_id_2>",
       "paper_count": 1, "first_collaboration": "<source_id>"}
    ]
  }
}
```

## 重要な設計判断

### 1. CITES のスコープ制御

マッパーは `existing_source_ids`（DB内に既にあるSource ID一覧）を受け取り、引用先がDB内に存在する場合のみCITESリレーションを生成する。DB外の論文に対するスタブSourceノードは作らない。

### 2. 著者名の重複解消

`generate_author_id("Saizhuo Wang", "academic")` は名前ベースのUUID5を返す。同名異人は区別されない。将来的にSemantic Scholarの`authorId`をAuthorノードのプロパティとして保存し、高精度の名寄せに使用する。

### 3. 非同期は将来対応

初期実装はsync（httpx.Client）のみ。バックフィル35本程度なら同期でも35秒（S2: 1 req/sec）。100本超になった時点でasync化を検討。

---

## 変更対象ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `scripts/emit_graph_queue.py` | SCHEMA_VERSION更新、cites/coauthored_with追加、map_papers登録 |
| `src/database/id_generator.py` | 変更なし（既存関数を再利用） |
| `src/academic/**` | **新規作成**（types, errors, s2_client, arxiv_client, cache, fetcher, mapper, cli） |
| `tests/academic/**` | **新規作成**（unit + property） |
| `pyproject.toml` | academic パッケージ登録 |
| `data/config/knowledge-graph-schema.yaml` | 変更なし（v2.1対応済み） |
| `CLAUDE.md` | パッケージ一覧に academic 追加 |

## 検証方法

1. **ユニットテスト**: `uv run pytest tests/academic/ -v`
2. **統合テスト**: `python -m academic fetch --arxiv-id 2303.09406` でS2 APIから取得確認
3. **graph-queue生成**: `uv run python scripts/emit_graph_queue.py --command academic-fetch --input .tmp/academic/papers.json` でJSON出力確認
4. **Neo4j投入**: `/save-to-graph` でMERGE投入後、Cypherクエリで確認:
   ```cypher
   MATCH (s:Source {source_type: 'paper'})-[:AUTHORED_BY]->(a:Author)
   RETURN s.title, collect(a.name) AS authors
   LIMIT 5
   ```
5. **品質チェック**: `make check-all`
