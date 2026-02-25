# EDINET DB ライブラリ実装計画

## Context

金融庁 EDINET の有価証券報告書データを構造化・提供する EDINET DB（https://edinetdb.jp）の REST API を活用し、全上場企業約 3,848 社の財務データをローカル DuckDB に保存するライブラリを `src/market/edinet/` に実装する。

**動機**: 日本の全上場企業の財務データ（24指標×最大6年分）、財務比率、AI分析、有報テキストを手元に持ち、分析に即座にアクセスできる環境を構築する。

**制約**: API は Beta プラン（1,000 回/日）。初回フルデータ取得には約 20 日かかるため、段階的に収集し、最終的にはデイリー増分更新で自動保持する。

---

## API 概要

| エンドポイント | 説明 | 認証 | 1回で得られるデータ |
|---|---|---|---|
| `GET /v1/search?q={query}` | 企業検索 | 不要 | 検索結果リスト |
| `GET /v1/companies?per_page=5000` | 全企業一覧 | 要 | 全3,848社（1コール） |
| `GET /v1/companies/{code}` | 企業詳細 + 最新財務 | 要 | 1社の基本情報 + 最新年度財務 |
| `GET /v1/companies/{code}/financials` | 財務時系列（最大6年） | 要 | 24指標 × 最大6年分 |
| `GET /v1/companies/{code}/ratios` | 財務比率時系列 | 要 | 13指標 × 最大6年分 |
| `GET /v1/companies/{code}/analysis` | 健全性スコア + AI所見 | 要 | スコア + ベンチマーク + AI解説 |
| `GET /v1/companies/{code}/text-blocks` | 有報テキスト | 要 | 事業概要・リスク・経営分析 |
| `GET /v1/rankings/{metric}` | 指標別ランキング | 要 | 18指標分 |
| `GET /v1/industries` | 業種一覧 | 要 | 34業種 + 平均指標 |
| `GET /v1/industries/{slug}` | 業種詳細 | 要 | 企業リスト + 業種平均 |

**認証**: `X-API-Key` ヘッダー。環境変数 `EDINET_DB_API_KEY` から読み込む。

**DB パス解決の優先順位**:

```
1. CLI 引数 --db-path（最優先）
2. 環境変数 EDINET_DB_PATH
3. get_db_path("duckdb", "edinet")（デフォルト）
   └─ DATA_DIR 環境変数 → data/duckdb/edinet.duckdb
```

---

## ディレクトリ構成

```
src/market/edinet/
├── __init__.py           # 公開 API エクスポート
├── constants.py          # URL, 環境変数名, メトリクス一覧, レート制限定数, DBパス定数
├── types.py              # データクラス（Config, Company, Financials, Ratios 等）
├── errors.py             # EdinetError 例外階層
├── client.py             # EdinetClient: HTTP + レート制限 + リトライ + 全10エンドポイント
├── storage.py            # EdinetStorage: DuckDB スキーマ初期化 + upsert/query
├── syncer.py             # EdinetSyncer: 6フェーズ初回同期 + デイリー増分 + レジューム
└── scripts/
    ├── __init__.py
    └── sync.py           # CLI ランナー（--initial, --daily, --status, --resume, --company, --db-path）

tests/market/unit/edinet/
├── __init__.py
├── test_client.py
├── test_types.py
├── test_errors.py
├── test_storage.py
└── test_syncer.py

data/duckdb/              # DuckDB ファイル + 付随状態ファイル（get_db_path パターン準拠）
├── edinet.duckdb         # デフォルト配置。--db-path / EDINET_DB_PATH で変更可能
├── _sync_state.json      # DB と同じディレクトリに自動配置
└── _rate_limit.json      # レート制限カウンター（同上）
```

---

## 主要コンポーネント設計

### 0. `constants.py` — 定数定義

```python
# API
DEFAULT_BASE_URL = "https://edinetdb.jp/api"
EDINET_API_KEY_ENV = "EDINET_DB_API_KEY"

# DB パス
EDINET_DB_PATH_ENV = "EDINET_DB_PATH"       # 環境変数でDBパスを外部指定
SYNC_STATE_FILENAME = "_sync_state.json"     # DB と同じディレクトリに自動配置
RATE_LIMIT_FILENAME = "_rate_limit.json"     # 同上

# レート制限
DAILY_RATE_LIMIT = 1000
SAFE_MARGIN = 50  # 実効上限 950 回/日
```

### 1. `errors.py` — 例外階層

NASDAQ パターン（`Exception` 直接継承、モジュールローカル）に準拠。

```
EdinetError (base)
├── EdinetAPIError        # HTTP 4xx/5xx（url, status_code, response_body）
├── EdinetRateLimitError  # 1,000回/日超過（calls_used, calls_limit）
├── EdinetValidationError # 入力検証（field, value）
└── EdinetParseError      # レスポンス解析失敗（raw_data）
```

`market/errors.py` に re-export + `ErrorCode` に `EDINET_API_ERROR`, `EDINET_RATE_LIMIT` を追加。

### 2. `types.py` — データモデル

| 型 | 用途 | パターン |
|---|---|---|
| `EdinetConfig` | API + DB パス設定（`resolved_db_path`, `sync_state_path` プロパティ含む） | `@dataclass(frozen=True)` |
| `RetryConfig` | リトライ設定 | `@dataclass(frozen=True)` |
| `Company` | `/companies` レスポンス | `@dataclass` |
| `FinancialRecord` | `/financials` 1年分 | `@dataclass`（24カラム） |
| `RatioRecord` | `/ratios` 1年分 | `@dataclass`（13カラム） |
| `AnalysisResult` | `/analysis` レスポンス | `@dataclass`（JSON含む） |
| `TextBlock` | `/text-blocks` 1年分 | `@dataclass` |
| `RankingEntry` | `/rankings` 1件 | `@dataclass` |
| `Industry` | `/industries` 1件 | `@dataclass` |
| `SyncProgress` | 同期進捗追跡 | `@dataclass` |

**`EdinetConfig` の DB パス解決**:

```python
@dataclass(frozen=True)
class EdinetConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 30.0
    polite_delay: float = 0.1
    db_path: Path | None = None  # None → 環境変数 → get_db_path() の順で解決

    @property
    def resolved_db_path(self) -> Path:
        """DB パスを解決する。優先順位: db_path > EDINET_DB_PATH > get_db_path()"""
        if self.db_path is not None:
            return self.db_path
        env_path = os.environ.get(EDINET_DB_PATH_ENV)
        if env_path:
            return Path(env_path)
        return get_db_path("duckdb", "edinet")

    @property
    def sync_state_path(self) -> Path:
        """同期状態ファイルのパス（DB と同じディレクトリに自動配置）"""
        return self.resolved_db_path.parent / SYNC_STATE_FILENAME
```

### 3. `client.py` — EdinetClient

```python
class EdinetClient:
    def __init__(self, config=None, retry_config=None) -> None: ...

    # --- 10 API メソッド ---
    def search(self, query: str) -> list[dict]: ...
    def list_companies(self, per_page=5000) -> list[Company]: ...
    def get_company(self, code: str) -> Company: ...
    def get_financials(self, code: str) -> list[FinancialRecord]: ...
    def get_ratios(self, code: str) -> list[RatioRecord]: ...
    def get_analysis(self, code: str) -> AnalysisResult: ...
    def get_text_blocks(self, code: str, year=None) -> list[TextBlock]: ...
    def get_ranking(self, metric: str) -> list[RankingEntry]: ...
    def list_industries(self) -> list[Industry]: ...
    def get_industry(self, slug: str) -> dict: ...

    # --- レート制限 ---
    def get_remaining_calls(self) -> int: ...
```

**HTTP実装**: `httpx` を使用（既存依存関係に含まれる）。

**レート制限**: `DailyRateLimiter` クラスで日次カウンターをJSONファイルに永続化。日付変更で自動リセット。安全マージン50コール（実効上限950回/日）。

**リトライ**: 指数バックオフ（初期2秒、最大60秒、3回まで）。5xxとネットワークエラーのみリトライ。

**リクエスト間隔**: 最低100msのインターバルでバースト防止。

### 4. `storage.py` — EdinetStorage (DuckDB)

既存の `database.db.DuckDBClient`（`store_df` の upsert 機能）を活用。

**初期化**: `EdinetConfig` から `resolved_db_path` を受け取る。

```python
class EdinetStorage:
    def __init__(self, config: EdinetConfig | None = None) -> None:
        config = config or EdinetConfig()
        self._client = DuckDBClient(config.resolved_db_path)
```

**テーブル構成**:

| テーブル | 主キー | 行数目安 |
|---|---|---|
| `companies` | `edinet_code` | ~3,848 |
| `financials` | `(edinet_code, fiscal_year)` | ~23,000（6年×3,848） |
| `ratios` | `(edinet_code, fiscal_year)` | ~23,000 |
| `analyses` | `edinet_code` | ~3,848 |
| `text_blocks` | `(edinet_code, fiscal_year)` | ~23,000 |
| `rankings` | `(metric, rank)` | ~69,000（18指標×3,848） |
| `industries` | `slug` | 34 |
| `industry_details` | `slug` | 34 |

**upsert**: `DuckDBClient.store_df(df, table, if_exists="upsert", key_columns=[...])` を使用。

**query メソッド**: `get_company()`, `get_financials()`, `get_all_company_codes()`, `query(sql)` 等。

### 5. `syncer.py` — EdinetSyncer（6フェーズ初回同期）

**初期化**: `EdinetConfig` から DB パスと同期状態パスを受け取る。

```python
class EdinetSyncer:
    def __init__(self, config: EdinetConfig | None = None) -> None:
        self._config = config or EdinetConfig()
        self._storage = EdinetStorage(self._config)
        self._client = EdinetClient(self._config)
        self._state_path = self._config.sync_state_path
```

#### 初回フルデータ同期（~20日間）

| Phase | 対象 | APIコール数 | 累計日数 | 優先度理由 |
|---|---|---|---|---|
| **1** | `/companies`（全件一括） | 1 | Day 1 | 全ての基盤（EDINETコード取得） |
| **2** | `/industries` + `/industries/{slug}` | 35 | Day 1 | 低コスト、セクター分析の基盤 |
| **3** | `/rankings/{metric}`（18指標） | 18 | Day 1 | 低コスト、高分析価値 |
| **4** | `/companies/{code}`（全~3,848社） | 3,848 | Day 1-4 | 企業詳細 + 最新財務を1コールで |
| **5** | `/financials` + `/ratios`（全社） | 7,696 | Day 5-12 | 時系列財務データ（最重要） |
| **6** | `/analysis` + `/text-blocks`（全社） | 7,696 | Day 13-20 | 健全性スコア + 有報テキスト |

**レジューム機能**: `_sync_state.json` に以下を永続化：
- 現在のフェーズ
- 完了済み EDINET コードのリスト
- 本日のAPIコール数と日付
- エラーリスト

レート制限到達時に graceful に停止し、翌日に同じコードの続きから再開。

**進捗報告**: 100社ごとにチェックポイント保存 + ログ出力。

#### デイリー増分同期

初回完了後の日次更新（~350-650コール/日で収まる）：

1. `/companies` で新規上場・上場廃止を検出（1コール）
2. `/rankings` を全更新（18コール）
3. `/industries` を週次更新（35コール/週）
4. 新規企業の全データ取得
5. 残り予算で古いデータの更新（`fetched_at` が30日以上前の企業を優先）

### 6. `scripts/sync.py` — CLI ランナー

```bash
# 初回フル同期開始（デフォルトパス: data/duckdb/edinet.duckdb）
uv run python -m market.edinet.scripts.sync --initial

# カスタムパス指定
uv run python -m market.edinet.scripts.sync --initial --db-path /data/edinet/custom.duckdb

# 環境変数指定
EDINET_DB_PATH=/data/edinet/custom.duckdb uv run python -m market.edinet.scripts.sync --initial

# デイリー増分同期
uv run python -m market.edinet.scripts.sync --daily

# 中断後の再開
uv run python -m market.edinet.scripts.sync --resume

# 同期状況の確認
uv run python -m market.edinet.scripts.sync --status

# 単一企業の同期
uv run python -m market.edinet.scripts.sync --company E02367

# 特定フェーズのみ実行
uv run python -m market.edinet.scripts.sync --phase financials_ratios
```

**`--db-path` 引数**:

```python
parser.add_argument(
    "--db-path",
    type=Path,
    default=None,
    help="DuckDB ファイルのパス（デフォルト: EDINET_DB_PATH 環境変数 または data/duckdb/edinet.duckdb）",
)

# 使用時
config = EdinetConfig(db_path=args.db_path)
syncer = EdinetSyncer(config=config)
```

---

## エラーリカバリ

| エラー | 対処 |
|---|---|
| HTTP 401 | `EdinetAPIError` → 同期停止（APIキー要修正） |
| HTTP 403 / 429 | `EdinetRateLimitError` → 本日の全リクエスト停止、進捗保存 |
| HTTP 404 | ログ警告 → その企業をスキップし続行 |
| HTTP 5xx | 指数バックオフで3回リトライ → 失敗なら記録して続行 |
| ネットワークエラー | 同上 |
| JSON パースエラー | `EdinetParseError` 記録 → スキップして続行 |
| プロセス中断 | `_sync_state.json` から自動レジューム |

---

## 既存コード再利用

| 再利用対象 | ファイルパス | 用途 |
|---|---|---|
| `DuckDBClient` | `src/database/db/duckdb_client.py` | `store_df()` の upsert、`query_df()` |
| `get_db_path()` | `src/database/db/connection.py` | DB パスのデフォルト解決（`DATA_DIR` 環境変数対応） |
| `NasdaqError` パターン | `src/market/nasdaq/errors.py` | 例外階層設計の参考 |
| `ErrorCode` enum | `src/market/errors.py` | EDINET用エラーコード追加 |
| `DataSource` enum | `src/market/types.py` | `EDINET_DB` 追加 |
| `get_logger()` | `src/utils_core/logging.py` | 構造化ロギング |
| `market/__init__.py` | `src/market/__init__.py` | EDINET クラスのエクスポート追加 |

---

## 変更が必要な既存ファイル

| ファイル | 変更内容 |
|---|---|
| `src/market/errors.py` | EDINET エラー re-export + `ErrorCode` に2項目追加 |
| `src/market/types.py` | `DataSource` に `EDINET_DB = "edinet_db"` 追加 |
| `src/market/__init__.py` | EDINET クラスのインポート・エクスポート追加 |

---

## 実装順序（Wave）

| Wave | ファイル | 依存 |
|---|---|---|
| **1** | `constants.py`, `errors.py`, `types.py`, `__init__.py`（空） | なし |
| **2** | `client.py`（DailyRateLimiter含む） | Wave 1 |
| **3** | `storage.py` | Wave 1 + `database.db.DuckDBClient` |
| **4** | `syncer.py` | Wave 2 + Wave 3 |
| **5** | `scripts/sync.py` | Wave 4 |
| **6** | 既存ファイル統合（`errors.py`, `types.py`, `__init__.py`） | Wave 5 |
| **並行** | 各 Wave のテスト | 対応する Wave |

---

## 検証方法

### 単体テスト
```bash
uv run pytest tests/market/unit/edinet/ -v
```

### 動作確認
```bash
# 1. 環境変数設定
export EDINET_DB_API_KEY="your_key_here"

# 2. 単一企業の取得テスト
uv run python -c "
from market.edinet import EdinetClient
client = EdinetClient()
company = client.get_company('E02367')
print(company)
financials = client.get_financials('E02367')
print(f'{len(financials)} years of data')
"

# 3. 初回同期開始（1日分で停止するため安全、デフォルトパス使用）
uv run python -m market.edinet.scripts.sync --initial

# 3b. カスタムパスで初回同期
uv run python -m market.edinet.scripts.sync --initial --db-path /tmp/edinet_test.duckdb

# 4. 同期状況確認
uv run python -m market.edinet.scripts.sync --status

# 5. 品質チェック
make check-all
```

### 統合確認
```bash
# DuckDB に保存されたデータのクエリ
uv run python -c "
from market.edinet import EdinetStorage
storage = EdinetStorage()
stats = storage.get_stats()
print(stats)
"
```
