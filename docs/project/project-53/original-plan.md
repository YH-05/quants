# Quants news_scraper パッケージを finance に移植する計画

## Context

Quants プロジェクト（`/Users/yukihata/Desktop/Quants/src/news_scraper/`）に CNBC・NASDAQ・yfinance からニュース記事を直接スクレイピングする `news_scraper` パッケージがある。Quants は finance に git 依存しているため、finance 側にこのパッケージを移植すれば Quants からも `from news_scraper import ...` で利用可能になる。

finance には既に `news` パッケージ（RSS 経由の収集パイプライン）と `rss` パッケージ（フィード管理インフラ）が存在するが、`news_scraper` は**スタンドアロンのスクレイピングライブラリ**であり、既存パイプラインとは統合しない。

## 方針

- **コピー＋アダプト**: Quants の 13 ファイルを `src/news_scraper/` にコピーし、finance 規約に適合させる
- **既存パッケージと統合しない**: `news`/`rss` パッケージとは独立を維持
- **API 互換性を保持**: 61 個の public export をすべて維持
- **Article は dataclass のまま**: Pydantic に変換しない（`news.Article` とは別物）

## 変更対象の全ファイル

### 1. pyproject.toml の更新

**ファイル**: `pyproject.toml`

```diff
 dependencies = [
+    # スクレイピング（news_scraper用）
+    "curl_cffi>=0.13.0",
+    "beautifulsoup4>=4.12.0",
+    "pyyaml>=6.0",
     ...
 ]

 [project.scripts]
+news-scraper = "news_scraper.finance_news_collect:main"

 [tool.hatch.build.targets.wheel]
-packages = ["src/analyze", ..., "src/notebooklm"]
+packages = ["src/analyze", ..., "src/notebooklm", "src/news_scraper"]
```

追加する依存:
| パッケージ | 理由 | 既存? |
|-----------|------|-------|
| `curl_cffi>=0.13.0` | ブラウザ偽装 HTTP クライアント | 未登録（推移的のみ） |
| `beautifulsoup4>=4.12.0` | HTML パース（フォールバック） | 未登録（trafilatura 経由） |
| `pyyaml>=6.0` | CLI の YAML 設定読み込み | 未登録 |

既に存在する依存（変更不要）:
`tenacity>=9.1.2`, `feedparser>=6.0.12`, `trafilatura>=2.0.0`, `yfinance>=0.2.0`, `pandas>=2.0.0`, `playwright>=1.49.0`（optional）

### 2. パッケージファイル（13 ファイル作成）

すべて `src/news_scraper/` に作成。ソースは `Quants/src/news_scraper/` からコピーし、以下の共通変更を適用:

**共通変更（全ファイル）**:
1. `import logging` / `logging.getLogger(__name__)` → `from utils_core.logging import get_logger` / `get_logger(__name__)`
2. f-string ログ `logger.info(f"msg {var}")` → structlog 形式 `logger.info("msg", key=var)`
3. モジュールパス参照 `src.news_scraper` → `news_scraper`

| # | ファイル | 元ファイル | 追加変更 |
|---|---------|-----------|---------|
| 1 | `__init__.py` | 同名 | AIDEV-NOTE 追加（`news.Article` との名前衝突について） |
| 2 | `__main__.py` | 同名 | モジュールパス修正 |
| 3 | `py.typed` | 新規 | 空ファイル（PEP 561） |
| 4 | `types.py` | 同名 | 変更なし（logging 不使用） |
| 5 | `exceptions.py` | 同名 | 変更なし（logging 不使用） |
| 6 | `session.py` | 同名 | 変更なし（logging 不使用） |
| 7 | `async_core.py` | 同名 | `gather_with_errors` の logger 型を `Any` に変更（structlog 互換） |
| 8 | `retry.py` | 同名 | 共通変更のみ |
| 9 | `cnbc.py` | 同名 | 共通変更のみ |
| 10 | `nasdaq.py` | 同名 | 共通変更のみ |
| 11 | `yfinance.py` | 同名 | 共通変更のみ |
| 12 | `unified.py` | 同名 | 共通変更のみ |
| 13 | `async_unified.py` | 同名 | 共通変更のみ |
| 14 | `finance_news_collect.py` | 同名 | 共通変更 + CLI ログ設定を structlog に変更 |

### 3. テスト構造（ディレクトリ + 初期テスト）

```
tests/news_scraper/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_types.py          # Article, ScraperConfig, constants, get_delay
│   ├── test_exceptions.py     # 例外階層, isinstance, 属性
│   ├── test_async_core.py     # RateLimiter, gather_with_errors
│   ├── test_retry.py          # classify_http_error, create_retry_decorator
│   └── test_session.py        # create_session, create_async_session
├── property/
│   ├── __init__.py
│   └── test_types_property.py # to_dict 不変条件, get_delay 範囲
└── integration/
    └── __init__.py
```

### 4. CLAUDE.md の更新

パッケージ一覧テーブルに追加:
```markdown
| `news_scraper` | 金融ニューススクレイパー | CNBC/NASDAQ/yfinance RSS・APIスクレイピング、curl_cffi、sync/async対応 |
```

依存関係に追加:
```markdown
- `news_scraper` (standalone、curl_cffi ベース)
```

## 実装順序

1. `pyproject.toml` 更新（依存追加 + wheel + scripts）
2. `src/news_scraper/` 作成（types → exceptions → session → async_core → retry → cnbc → nasdaq → yfinance → unified → async_unified → finance_news_collect → __init__ → __main__ → py.typed）
3. `tests/news_scraper/` 作成（構造 + 単体テスト + プロパティテスト）
4. `make check-all` で品質確認
5. CLAUDE.md 更新

## 検証方法

```bash
# 1. 依存インストール
uv sync --all-extras

# 2. インポートテスト
python -c "from news_scraper import Article, ScraperConfig, collect_financial_news; print('OK')"

# 3. テスト実行
uv run pytest tests/news_scraper/ -v

# 4. 品質チェック
make check-all

# 5. CLI 動作確認
news-scraper --help
```
