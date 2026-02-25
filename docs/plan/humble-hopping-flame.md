# EDINET DB ライブラリ実装計画 — DB パス外部指定化の修正

## Context

`docs/plan/2026-02-25_edinet-db-library.md` の実装計画では、DuckDB ファイルと同期状態ファイルのパスが `data/raw/edinet/` にハードコードされている。テスト環境・本番環境・カスタム配置に対応するため、**CLI引数 + 環境変数** でDBパスを外部から指定可能にする。

**方針**:
- CLI: `--db-path /path/to/edinet.duckdb`
- 環境変数: `EDINET_DB_PATH`
- デフォルト: 既存の `get_db_path("duckdb", "edinet")` → `data/duckdb/edinet.duckdb`
- `_sync_state.json` は DB ファイルと同じディレクトリに自動配置

---

## 修正箇所

### 1. `constants.py` に追加

**現計画**: URL、環境変数名、メトリクス一覧、レート制限定数のみ

**修正**: DB パス関連の定数を追加

```python
# DB パス環境変数名
EDINET_DB_PATH_ENV = "EDINET_DB_PATH"

# 同期状態ファイル名
SYNC_STATE_FILENAME = "_sync_state.json"

# レート制限状態ファイル名
RATE_LIMIT_FILENAME = "_rate_limit.json"
```

### 2. `types.py` — `EdinetConfig` に `db_path` フィールド追加

**現計画**: `EdinetConfig` は API クライアント設定のみ

**修正**: `db_path` を追加し、Storage・Syncer・CLI 全体で利用可能にする

```python
@dataclass(frozen=True)
class EdinetConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    timeout: float = 30.0
    polite_delay: float = 0.1
    db_path: Path | None = None  # ← 追加。None の場合は get_db_path() を使用

    @property
    def resolved_db_path(self) -> Path:
        """DB パスを解決する。優先順位: db_path > 環境変数 > デフォルト"""
        if self.db_path is not None:
            return self.db_path
        env_path = os.environ.get(EDINET_DB_PATH_ENV)
        if env_path:
            return Path(env_path)
        return get_db_path("duckdb", "edinet")

    @property
    def sync_state_path(self) -> Path:
        """同期状態ファイルのパス（DB と同じディレクトリ）"""
        return self.resolved_db_path.parent / SYNC_STATE_FILENAME
```

### 3. `storage.py` — `EdinetStorage` のパス解決変更

**現計画**: `data/raw/edinet/edinet.duckdb` ハードコード想定

**修正**: `EdinetConfig` から `resolved_db_path` を受け取る

```python
class EdinetStorage:
    def __init__(self, config: EdinetConfig | None = None) -> None:
        config = config or EdinetConfig()
        self._client = DuckDBClient(config.resolved_db_path)
```

### 4. `syncer.py` — 同期状態ファイルのパス解決変更

**現計画**: `data/raw/edinet/_sync_state.json` ハードコード想定

**修正**: `EdinetConfig.sync_state_path` を使用

```python
class EdinetSyncer:
    def __init__(self, config: EdinetConfig | None = None) -> None:
        self._config = config or EdinetConfig()
        self._storage = EdinetStorage(self._config)
        self._client = EdinetClient(self._config)
        self._state_path = self._config.sync_state_path
```

### 5. `scripts/sync.py` — CLI 引数追加

**現計画**: `--initial`, `--daily`, `--status`, `--resume`, `--company`, `--phase`

**修正**: `--db-path` を追加

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

**CLI 例の更新**:
```bash
# デフォルトパス（data/duckdb/edinet.duckdb）
uv run python -m market.edinet.scripts.sync --initial

# カスタムパス指定
uv run python -m market.edinet.scripts.sync --initial --db-path /data/edinet/custom.duckdb

# 環境変数指定
EDINET_DB_PATH=/data/edinet/custom.duckdb uv run python -m market.edinet.scripts.sync --initial
```

### 6. 計画書のディレクトリ構成セクション修正

**現計画**:
```
data/raw/edinet/
├── edinet.duckdb
└── _sync_state.json
```

**修正後**（デフォルト配置）:
```
data/duckdb/
└── edinet.duckdb          # DuckDB ファイル（get_db_path パターン準拠）

data/duckdb/
└── _sync_state.json       # DB と同じディレクトリに自動配置
└── _rate_limit.json       # レート制限カウンター
```

---

## パス解決の優先順位

```
1. CLI 引数 --db-path（最優先）
2. 環境変数 EDINET_DB_PATH
3. get_db_path("duckdb", "edinet")（デフォルト）
   └─ DATA_DIR 環境変数 → data/duckdb/edinet.duckdb
```

---

## 対象ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `docs/plan/2026-02-25_edinet-db-library.md` | 上記6箇所の反映 |

---

## 検証方法

計画書の修正のみのため、コード変更なし。修正後に以下を確認:

1. パス解決の優先順位が明記されているか
2. `EdinetConfig.resolved_db_path` のフローが一貫しているか
3. デフォルトパスが既存の `get_db_path()` パターンに準拠しているか
4. CLI 例が更新されているか
