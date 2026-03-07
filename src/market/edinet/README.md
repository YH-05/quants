# market.edinet

金融庁に提出された有価証券報告書から抽出した構造化財務データを提供する EDINET DB API（https://edinetdb.jp）の Python クライアントモジュール。

## 概要

このモジュールは、日本の上場企業（約 3,848 社）の財務データに REST API 経由でアクセスするための機能を提供します。

**取得可能なデータ:**

- **企業情報**: EDINET コード・証券コード・業種・上場ステータス
- **財務データ（年次）**: P/L・B/S・CF・1株指標・比率・その他の 30 フィールド（最大 6 期分、会計基準に応じて Optional）
- **財務比率**: 収益性・BS・配当・効率性・1株指標・バリュエーション・CF・従業員生産性の 21 フィールド（最大 6 期分）
- **ランキング**: 指標別企業ランキング（20 指標対応）
- **テキスト**: 事業概要・リスク要因・経営者分析（有価証券報告書から抽出）
- **AI 分析**: 財務健全性スコアと AI 生成コメンタリー
- **業種マスタ**: 34 業種分類の詳細情報

## インストール

このモジュールは `market` パッケージの一部です。

```bash
# リポジトリ全体の依存関係をインストール
uv sync --all-extras
```

## 設定

### API キーの取得

EDINET DB API を使用するには API キーが必要です。

1. [EDINET DB](https://edinetdb.jp) にアクセス
2. アカウントを作成し API キーを発行
3. プランに応じた日次 API コール上限を確認（Free: 100件/日、Pro: 1,000件/日、Business: 10,000件/日）

### API キーの設定

**方法1: 環境変数（推奨）**

```bash
export EDINET_DB_API_KEY="your_api_key_here"
```

**方法2: .env ファイル**

```bash
# .env ファイルに追加
EDINET_DB_API_KEY=your_api_key_here
```

**方法3: コード内で直接指定**

```python
from market.edinet import EdinetClient, EdinetConfig

config = EdinetConfig(api_key="your_api_key_here")
```

## クイックスタート

### 5分で試せる基本的な使い方

```python
import os
from market.edinet import EdinetClient, EdinetConfig

# 1. 設定を作成（環境変数から API キーを読み込み）
config = EdinetConfig(api_key=os.environ["EDINET_DB_API_KEY"])

# 2. クライアントをコンテキストマネージャで使用
with EdinetClient(config=config) as client:
    # 3. 企業一覧を取得（約 3,848 社）
    companies = client.list_companies()
    print(f"企業数: {len(companies)}")

    # 4. 特定企業（例: トヨタ自動車）の財務データを取得
    # まずキーワード検索でEDINETコードを調べる
    results = client.search("トヨタ")
    edinet_code = results[0]["edinet_code"]

    # 5. 年次財務データを取得（最大6期分、30フィールド）
    #    全指標フィールドは Optional（会計基準により None の場合あり）
    financials = client.get_financials(edinet_code)
    latest = financials[0]
    if latest.revenue is not None:
        print(f"売上高: {latest.revenue:,.0f} 円")
    if latest.operating_income is not None:
        print(f"営業利益: {latest.operating_income:,.0f} 円")
    if latest.net_income is not None:
        print(f"純利益: {latest.net_income:,.0f} 円")
```

**出力例:**

```
企業数: 3848
売上高: 45,095,325,000,000 円
営業利益: 5,352,934,000,000 円
純利益: 4,944,286,000,000 円
```

---

## 機能別セクション

### 企業情報取得

```python
with EdinetClient(config=config) as client:
    # 全企業一覧を取得
    companies = client.list_companies()
    for company in companies[:3]:
        print(f"{company.corp_name} ({company.edinet_code}) - {company.industry_name}")

    # EDINET コードで特定企業を取得
    company = client.get_company("E02529")
    print(f"企業名: {company.corp_name}")
    print(f"証券コード: {company.sec_code}")
    print(f"上場ステータス: {company.listing_status}")

    # キーワード検索
    results = client.search("ソニー")
    for r in results:
        print(f"  {r['corp_name']} - EDINET: {r['edinet_code']}")
```

`Company` の主要フィールド:

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `edinet_code` | EDINET コード（主キー） | `"E02529"` |
| `sec_code` | 証券コード | `"67580"` |
| `corp_name` | 企業名（日本語） | `"ソニーグループ株式会社"` |
| `industry_code` | 業種コード | `"3050"` |
| `industry_name` | 業種名（日本語） | `"情報・通信業"` |
| `listing_status` | 上場ステータス | `"上場"` |

### 財務データ取得（30 フィールドの年次財務データ）

```python
with EdinetClient(config=config) as client:
    # 最大6期分の年次財務データを取得
    # 全指標フィールドは Optional（会計基準により None の場合あり）
    records = client.get_financials("E02529")
    for r in records:
        rev = f"{r.revenue:,.0f}" if r.revenue is not None else "N/A"
        ni = f"{r.net_income:,.0f}" if r.net_income is not None else "N/A"
        print(f"FY{r.fiscal_year}: 売上高={rev}, 純利益={ni}")

        eps_s = f"{r.eps:.1f}円" if r.eps is not None else "N/A"
        bps_s = f"{r.bps:.1f}円" if r.bps is not None else "N/A"
        dps = f"{r.dividend_per_share:.1f}円" if r.dividend_per_share is not None else "N/A"
        print(f"  EPS={eps_s}, BPS={bps_s}, 配当={dps}")

        if r.accounting_standard is not None:
            print(f"  会計基準: {r.accounting_standard}")
```

`FinancialRecord` の 30 フィールド:

> **必須フィールド**: `edinet_code` と `fiscal_year` のみ。
> 全指標フィールドは `Optional`（`None` デフォルト）。会計基準（JP GAAP / US GAAP / IFRS）により
> API の返却フィールドが異なるため、存在しないフィールドは `None` になります。

| カテゴリ | フィールド | 型 | 説明 |
|---------|-----------|-----|------|
| キー | `edinet_code` | `str` | EDINET コード（必須） |
| | `fiscal_year` | `int` | 会計年度（必須、例: `2025`） |
| 損益計算書 | `revenue` | `float \| None` | 売上高（円） |
| | `operating_income` | `float \| None` | 営業利益（円）JP GAAP のみ |
| | `ordinary_income` | `float \| None` | 経常利益（円） |
| | `net_income` | `float \| None` | 当期純利益（円） |
| | `profit_before_tax` | `float \| None` | 税引前利益（円） |
| | `comprehensive_income` | `float \| None` | 包括利益（円） |
| 貸借対照表 | `total_assets` | `float \| None` | 総資産（円） |
| | `net_assets` | `float \| None` | 純資産（円） |
| | `shareholders_equity` | `float \| None` | 自己資本（円） |
| | `cash` | `float \| None` | 現金及び現金同等物（円） |
| | `goodwill` | `float \| None` | のれん（円）JP GAAP のみ |
| キャッシュフロー | `cf_operating` | `float \| None` | 営業 CF（円） |
| | `cf_investing` | `float \| None` | 投資 CF（円） |
| | `cf_financing` | `float \| None` | 財務 CF（円） |
| 1株当たり | `eps` | `float \| None` | 1株当たり利益 |
| | `diluted_eps` | `float \| None` | 希薄化後 EPS |
| | `bps` | `float \| None` | 1株当たり純資産 |
| | `dividend_per_share` | `float \| None` | 1株当たり配当 |
| 比率 | `equity_ratio_official` | `float \| None` | 自己資本比率（%、会社公表値） |
| | `payout_ratio` | `float \| None` | 配当性向（%） |
| | `per` | `float \| None` | 株価収益率 |
| | `roe_official` | `float \| None` | 自己資本利益率（%、会社公表値） |
| その他 | `num_employees` | `int \| None` | 従業員数 |
| | `capex` | `float \| None` | 設備投資（円）JP GAAP のみ |
| | `depreciation` | `float \| None` | 減価償却費（円）JP GAAP のみ |
| | `rnd_expenses` | `float \| None` | 研究開発費（円）JP GAAP のみ |
| | `accounting_standard` | `str \| None` | 会計基準（`"JP GAAP"` / `"US GAAP"` / `"IFRS"`） |
| | `submit_date` | `str \| None` | 提出日（例: `"2025-06-15"`） |

### 財務比率取得（21 フィールドの財務比率）

```python
with EdinetClient(config=config) as client:
    # 最大6期分の財務比率を取得
    # 全比率フィールドは Optional（企業・年度により None の場合あり）
    ratios = client.get_ratios("E02529")
    latest = ratios[0]

    if latest.roe is not None:
        print(f"ROE: {latest.roe:.1f}%")
    if latest.roa is not None:
        print(f"ROA: {latest.roa:.1f}%")
    if latest.net_margin is not None:
        print(f"純利益率: {latest.net_margin:.1f}%")
    if latest.equity_ratio is not None:
        print(f"自己資本比率: {latest.equity_ratio:.1f}%")
    if latest.dividend_yield is not None:
        print(f"配当利回り: {latest.dividend_yield:.1f}%")
```

`RatioRecord` の 21 フィールド:

> **必須フィールド**: `edinet_code` と `fiscal_year` のみ。
> 全比率フィールドは `Optional`（`None` デフォルト）。

| カテゴリ | フィールド | 型 | 説明 |
|---------|-----------|-----|------|
| キー | `edinet_code` | `str` | EDINET コード（必須） |
| | `fiscal_year` | `int` | 会計年度（必須） |
| 収益性 | `roe` | `float \| None` | 自己資本利益率（%） |
| | `roa` | `float \| None` | 総資産利益率（%） |
| | `roe_official` | `float \| None` | 会社公表 ROE（%） |
| | `net_margin` | `float \| None` | 純利益率（%） |
| 貸借対照表 | `equity_ratio` | `float \| None` | 自己資本比率（%） |
| | `equity_ratio_official` | `float \| None` | 会社公表自己資本比率（%） |
| 配当 | `payout_ratio` | `float \| None` | 配当性向（%） |
| | `dividend_per_share` | `float \| None` | 1株当たり配当 |
| | `adjusted_dividend_per_share` | `float \| None` | 調整後1株配当（株式分割調整済） |
| | `dividend_yield` | `float \| None` | 配当利回り（%） |
| 効率性 | `asset_turnover` | `float \| None` | 総資産回転率 |
| 1株指標 | `eps` | `float \| None` | 1株当たり利益 |
| | `diluted_eps` | `float \| None` | 希薄化後 EPS |
| | `bps` | `float \| None` | 1株当たり純資産 |
| バリュエーション | `per` | `float \| None` | 株価収益率 |
| キャッシュフロー | `fcf` | `float \| None` | フリーキャッシュフロー（円） |
| 従業員生産性 | `net_income_per_employee` | `float \| None` | 従業員1人当たり純利益 |
| | `revenue_per_employee` | `float \| None` | 従業員1人当たり売上高 |
| 調整係数 | `split_adjustment_factor` | `float \| None` | 株式分割調整係数 |

### ランキング取得（指標別企業ランキング）

```python
with EdinetClient(config=config) as client:
    # ROE ランキング上位10社を取得
    entries = client.get_ranking("roe")
    for entry in entries[:10]:
        print(f"#{entry.rank:3d} {entry.corp_name}: {entry.value:.1f}%")

    # 売上高ランキングを取得
    revenue_rank = client.get_ranking("revenue")
    print(f"\n売上高1位: {revenue_rank[0].corp_name}")
```

利用可能なランキング指標（20種）:

| カテゴリ | 指標名 | 説明 |
|---------|--------|------|
| 収益性 | `roe` | 自己資本利益率 |
| | `operating-margin` | 営業利益率 |
| | `net-margin` | 純利益率 |
| | `roa` | 総資産利益率 |
| バリュエーション | `per` | 株価収益率 |
| | `eps` | 1株当たり利益 |
| 株主還元 | `dividend-yield` | 配当利回り |
| | `payout-ratio` | 配当性向 |
| キャッシュフロー | `free-cf` | フリーキャッシュフロー |
| 規模 | `revenue` | 売上高 |
| 財務健全性 | `health-score` | 財務健全性スコア |
| | `credit-score` | クレジットスコア |
| | `equity-ratio` | 自己資本比率 |
| 成長率（前年比） | `revenue-growth` | 売上高成長率 |
| | `ni-growth` | 純利益成長率 |
| | `eps-growth` | EPS 成長率 |
| 成長率（3年 CAGR） | `revenue-cagr-3y` | 売上高 3 年 CAGR |
| | `oi-cagr-3y` | 営業利益 3 年 CAGR |
| | `ni-cagr-3y` | 純利益 3 年 CAGR |
| | `eps-cagr-3y` | EPS 3 年 CAGR |

### テキスト抽出（有価証券報告書テキスト）

```python
with EdinetClient(config=config) as client:
    # 有価証券報告書のテキストを取得
    blocks = client.get_text_blocks("E02529")
    latest_block = blocks[0]
    print(f"FY{latest_block.fiscal_year} 事業概要:")
    print(latest_block.business_overview[:200])

    print("\nリスク要因:")
    print(latest_block.risk_factors[:200])

    # 特定年度を指定して取得
    blocks_2024 = client.get_text_blocks("E02529", year="2024")
```

`TextBlock` のフィールド:

| フィールド | 説明 |
|-----------|------|
| `edinet_code` | EDINET コード |
| `fiscal_year` | 会計年度 |
| `business_overview` | 事業の内容（事業概要テキスト） |
| `risk_factors` | 事業等のリスク |
| `management_analysis` | 経営者による分析 |

### AI 分析結果取得（財務健全性分析）

```python
with EdinetClient(config=config) as client:
    # AI 生成の財務健全性分析を取得
    analysis = client.get_analysis("E02529")
    print(f"財務健全性スコア: {analysis.health_score:.1f} / 100")
    print(f"ベンチマーク比較: {analysis.benchmark_comparison}")
    print(f"AI コメンタリー: {analysis.commentary}")
```

`AnalysisResult` のフィールド:

| フィールド | 説明 | 例 |
|-----------|------|-----|
| `edinet_code` | EDINET コード | `"E02529"` |
| `health_score` | 財務健全性スコア（0〜100） | `75.0` |
| `benchmark_comparison` | ベンチマーク比較 | `"above_average"` |
| `commentary` | AI 生成コメンタリー | テキスト |

### データ永続化（EdinetStorage）

`EdinetStorage` は DuckDB バックエンドで 8 テーブルを管理し、API から取得したデータをローカルに永続化します。

```python
from pathlib import Path
from market.edinet import EdinetConfig, EdinetStorage

# DuckDB ファイルを指定してストレージを初期化
config = EdinetConfig(
    api_key="your_key",
    db_path=Path("data/edinet.duckdb"),
)
storage = EdinetStorage(config=config)

# テーブルの行数を確認
stats = storage.get_stats()
for table, count in stats.items():
    print(f"  {table}: {count} 行")

# 企業データを検索
company_df = storage.get_company("E02529")
if company_df is not None:
    print(company_df)

# 財務データを検索
financials_df = storage.get_financials("E02529")

# 全 EDINET コードを取得
all_codes = storage.get_all_company_codes()
print(f"登録済み企業数: {len(all_codes)}")

# 任意の SELECT クエリを実行
df = storage.query("""
    SELECT corp_name, industry_name
    FROM companies
    WHERE listing_status = '上場'
    ORDER BY corp_name
    LIMIT 10
""")
```

管理する 8 テーブル:

| テーブル名 | 説明 | 主キー |
|-----------|------|--------|
| `companies` | 企業マスタ（約 3,848 件） | `edinet_code` |
| `financials` | 年次財務データ（30 フィールド） | `(edinet_code, fiscal_year)` |
| `ratios` | 財務比率（21 フィールド） | `(edinet_code, fiscal_year)` |
| `analyses` | AI 財務健全性分析 | `edinet_code` |
| `text_blocks` | 有価証券報告書テキスト | `(edinet_code, fiscal_year)` |
| `rankings` | 指標別ランキング（20 指標） | `(metric, rank)` |
| `industries` | 業種マスタ（34 分類） | `slug` |
| `industry_details` | 業種詳細データ | `slug` |

### 同期オーケストレーション（EdinetSyncer）

`EdinetSyncer` は API から DuckDB への完全な 6 フェーズ同期を管理します。中断しても `_sync_state.json` のチェックポイントから再開できます。

```python
from pathlib import Path
from market.edinet import EdinetConfig, EdinetSyncer

config = EdinetConfig(
    api_key="your_key",
    db_path=Path("data/edinet.duckdb"),
)
syncer = EdinetSyncer(config=config)

# 初回: 6フェーズ全同期（約 19,000 API コール）
results = syncer.run_initial()
for result in results:
    status = "OK" if result.success else "FAIL"
    print(f"[{status}] {result.phase}: {result.companies_processed} 件処理")

# 毎日の差分同期（企業リスト + 財務データ更新）
results = syncer.run_daily()

# 中断した同期をチェックポイントから再開
results = syncer.resume()

# 特定企業だけ同期
result = syncer.sync_company("E02529")

# 同期状況の確認
status = syncer.get_status()
print(f"現在のフェーズ: {status['current_phase']}")
print(f"本日の API コール数: {status['today_api_calls']}")
print(f"残り API コール数: {status['remaining_api_calls']}")
```

6 フェーズの内訳:

| フェーズ | 説明 | API コール数 |
|---------|------|-------------|
| 1. `companies` | 全企業一覧取得 | 1 |
| 2. `industries` | 業種マスタ + 詳細取得 | 約 35 |
| 3. `rankings` | 20 指標のランキング取得 | 20 |
| 4. `company_details` | 全企業の詳細取得 | 約 3,848 |
| 5. `financials_ratios` | 全企業の財務データ + 比率取得 | 約 7,696 |
| 6. `analysis_text` | 全企業の AI 分析 + テキスト取得 | 約 7,696 |

**チェックポイント**: 100 社処理ごとに `_sync_state.json` に進捗を保存。レート制限に達した場合も自動保存して停止。

### CLI での使用

```bash
# 初回: 6フェーズ全同期
uv run python -m market.edinet.scripts.sync --initial

# 毎日の差分同期
uv run python -m market.edinet.scripts.sync --daily

# 中断した同期を再開
uv run python -m market.edinet.scripts.sync --resume

# 同期状況を確認
uv run python -m market.edinet.scripts.sync --status

# 特定企業だけ同期
uv run python -m market.edinet.scripts.sync --company E02529

# カスタム DuckDB パス指定
uv run python -m market.edinet.scripts.sync --initial --db-path /data/edinet.duckdb
```

### DailyRateLimiter（日次 API 制限管理）

```python
from pathlib import Path
from market.edinet.rate_limiter import DailyRateLimiter

# 日次レート制限管理（デフォルト: 1,000件/日、安全マージン 50件）
limiter = DailyRateLimiter(
    state_path=Path("data/_rate_limit.json"),
    daily_limit=1000,
    safe_margin=50,
)

# 残り呼び出し回数を確認
remaining = limiter.get_remaining()
print(f"残り API コール数: {remaining}")  # 例: 950

# 呼び出しが許可されているか確認
if limiter.is_allowed():
    # API 呼び出しを実行
    limiter.record_call()

# 日付をまたいだ場合にカウンタをリセット
limiter.reset_if_new_day()

# 状態を強制保存
limiter.flush()
```

---

## API リファレンス

### EdinetClient

EDINET DB API の全 10 エンドポイントに対応する同期 HTTP クライアント。

**コンストラクタ:**

```python
EdinetClient(
    config: EdinetConfig | None = None,
    retry_config: RetryConfig | None = None,
    rate_limiter: DailyRateLimiter | None = None,
)
```

`config` が `None` の場合、環境変数 `EDINET_DB_API_KEY` から API キーを読み込みます。

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `search(query)` | 企業名・キーワードで検索（`GET /v1/search`） | `list[dict]` |
| `list_companies(per_page=5000)` | 全企業一覧を取得（`GET /v1/companies`） | `list[Company]` |
| `get_company(code)` | EDINET コードで企業を取得（`GET /v1/companies/{code}`） | `Company` |
| `get_financials(code)` | 年次財務データを取得（`GET /v1/companies/{code}/financials`、30 フィールド） | `list[FinancialRecord]` |
| `get_ratios(code)` | 財務比率を取得（`GET /v1/companies/{code}/ratios`、21 フィールド） | `list[RatioRecord]` |
| `get_analysis(code)` | AI 財務健全性分析を取得（`GET /v1/companies/{code}/analysis`） | `AnalysisResult` |
| `get_text_blocks(code, year=None)` | 有価証券報告書テキストを取得（`GET /v1/companies/{code}/text-blocks`） | `list[TextBlock]` |
| `get_ranking(metric)` | 指標別ランキングを取得（`GET /v1/rankings/{metric}`） | `list[RankingEntry]` |
| `list_industries()` | 業種マスタ一覧を取得（`GET /v1/industries`） | `list[Industry]` |
| `get_industry(slug)` | 業種詳細を取得（`GET /v1/industries/{slug}`） | `dict` |
| `get_remaining_calls()` | 本日の残り API コール数を取得 | `int \| None` |
| `close()` | HTTP クライアントを閉じる | `None` |

### EdinetConfig

EDINET DB API クライアントの設定クラス（イミュータブル）。

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `api_key` | `str` | 必須 | API キー（`X-API-Key` ヘッダーとして送信） |
| `base_url` | `str` | `"https://edinetdb.jp"` | API のベース URL |
| `timeout` | `float` | `30.0` | HTTP タイムアウト（秒）。1.0〜300.0 |
| `polite_delay` | `float` | `0.1` | リクエスト間の待機時間（秒）。0.0〜60.0 |
| `db_path` | `Path \| None` | `None` | DuckDB ファイルパス。None の場合は環境変数または `get_db_path()` を使用 |

**プロパティ:**

| プロパティ | 説明 |
|-----------|------|
| `resolved_db_path` | DuckDB ファイルパスを優先順位に従って解決（明示指定 > 環境変数 > デフォルト） |
| `sync_state_path` | 同期状態ファイル（`_sync_state.json`）のパス |

### RetryConfig

リトライ動作の設定クラス（イミュータブル）。

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `max_attempts` | `int` | `3` | 最大試行回数（1〜10） |
| `initial_delay` | `float` | `1.0` | 初回リトライまでの待機時間（秒） |
| `max_delay` | `float` | `30.0` | リトライ間の最大待機時間（秒） |
| `exponential_base` | `float` | `2.0` | 指数バックオフの基数 |
| `jitter` | `bool` | `True` | ランダムジッターを追加するか |

**リトライ対象:**

- HTTP 5xx サーバーエラー
- `httpx.ConnectError`（接続エラー）
- `httpx.TimeoutException`（タイムアウト）

**リトライ非対象（即時例外）:**

- HTTP 4xx クライアントエラー（400, 403, 404 等）
- HTTP 429 レート制限エラー

### EdinetStorage

DuckDB ストレージ管理クラス。スキーマの自動マイグレーション機構を内蔵。

| メソッド | 説明 |
|---------|------|
| `ensure_tables()` | 8テーブルを作成し、既存テーブルのスキーママイグレーションを実行 |
| `upsert_companies(companies)` | 企業データをアップサート |
| `upsert_financials(records)` | 財務データをアップサート |
| `upsert_ratios(records)` | 財務比率をアップサート |
| `upsert_analyses(analyses)` | AI 分析結果をアップサート |
| `upsert_text_blocks(blocks)` | テキストブロックをアップサート |
| `upsert_rankings(entries)` | ランキングをアップサート |
| `upsert_industries(industries)` | 業種マスタをアップサート |
| `upsert_industry_details(details_df)` | 業種詳細をアップサート |
| `get_company(edinet_code)` | 企業データを取得（DataFrame） |
| `get_financials(edinet_code)` | 財務データを取得（DataFrame） |
| `get_all_company_codes()` | 全 EDINET コードを取得 |
| `get_stats()` | 全 8 テーブルの行数を取得 |
| `query(sql)` | SELECT クエリを実行（SELECT のみ許可） |

### EdinetSyncer

6 フェーズ同期オーケストレーター。

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `run_initial()` | 6フェーズ全同期を実行 | `list[SyncResult]` |
| `run_daily()` | 日次差分同期を実行（企業リスト + 財務データ） | `list[SyncResult]` |
| `resume()` | チェックポイントから同期を再開 | `list[SyncResult]` |
| `sync_company(code)` | 特定企業のデータを同期 | `SyncResult` |
| `get_status()` | 現在の同期状況を取得 | `dict` |

`SyncResult` フィールド:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `phase` | `str` | 完了または中断したフェーズ名 |
| `success` | `bool` | フェーズが成功したか |
| `companies_processed` | `int` | 処理した企業数 |
| `errors` | `tuple[str, ...]` | エラーメッセージのタプル |
| `stopped_reason` | `str \| None` | 停止理由（`"rate_limit"` または `None`） |

### 例外クラス

| 例外 | 説明 |
|------|------|
| `EdinetError` | 全 EDINET 例外の基底クラス |
| `EdinetAPIError` | HTTP 4xx/5xx エラー時（`url`, `status_code`, `response_body` 属性あり） |
| `EdinetRateLimitError` | 日次 API コール上限超過時（`calls_used`, `calls_limit` 属性あり） |
| `EdinetValidationError` | 入力バリデーションエラー時（`field`, `value` 属性あり） |
| `EdinetParseError` | API レスポンスのパースエラー時（`raw_data` 属性あり） |

---

## マイグレーション手順

### 旧バージョンからの移行

`FinancialRecord` と `RatioRecord` のフィールド定義が公式 API 仕様に基づき全面更新されています。既存コードの更新が必要な場合があります。

#### フィールド名の変更

| 旧フィールド名 | 新フィールド名 | 対象 |
|---------------|---------------|------|
| `operating_cf` | `cf_operating` | FinancialRecord |
| `investing_cf` | `cf_investing` | FinancialRecord |
| `financing_cf` | `cf_financing` | FinancialRecord |
| `employees` | `num_employees` | FinancialRecord |
| `rnd_expense` | `rnd_expenses` | FinancialRecord |
| `equity` | `shareholders_equity` | FinancialRecord |

#### 削除されたフィールド

以下のフィールドは API 検証の結果、実際の API レスポンスに存在しないことが確認されたため削除されました。

| 旧フィールド | 代替 | 備考 |
|-------------|------|------|
| `interest_bearing_debt` | なし | API 未提供 |
| `free_cf` | `RatioRecord.fcf` | ratios エンドポイントで提供 |
| `shares_outstanding` | なし | API 未提供 |
| `period_type` | なし | API 未提供（全レコード annual） |
| `operating_margin` | `RatioRecord.net_margin` | ratios エンドポイントで提供 |
| `debt_equity_ratio` | なし | API 未提供 |
| `current_ratio` | なし | API 未提供 |
| `interest_coverage_ratio` | なし | API 未提供 |
| `revenue_growth` | なし | API 未提供 |
| `operating_income_growth` | なし | API 未提供 |
| `net_income_growth` | なし | API 未提供 |

#### 新規追加フィールド（FinancialRecord）

| フィールド | 説明 |
|-----------|------|
| `profit_before_tax` | 税引前利益 |
| `comprehensive_income` | 包括利益 |
| `shareholders_equity` | 自己資本（旧 `equity`） |
| `cash` | 現金及び現金同等物 |
| `diluted_eps` | 希薄化後 EPS |
| `equity_ratio_official` | 会社公表自己資本比率（%） |
| `payout_ratio` | 配当性向（%） |
| `per` | 株価収益率 |
| `roe_official` | 会社公表 ROE（%） |
| `accounting_standard` | 会計基準 |
| `submit_date` | 提出日 |

#### 新規追加フィールド（RatioRecord）

| フィールド | 説明 |
|-----------|------|
| `roe_official` | 会社公表 ROE |
| `equity_ratio_official` | 会社公表自己資本比率 |
| `adjusted_dividend_per_share` | 調整後1株配当 |
| `dividend_yield` | 配当利回り |
| `diluted_eps` | 希薄化後 EPS |
| `fcf` | フリーキャッシュフロー |
| `net_income_per_employee` | 従業員1人当たり純利益 |
| `revenue_per_employee` | 従業員1人当たり売上高 |
| `split_adjustment_factor` | 株式分割調整係数 |

#### Optional 扱いへの変更

**重要**: 全指標フィールドが `Optional`（`None` デフォルト）に変更されました。会計基準（JP GAAP / US GAAP / IFRS）によって API が返すフィールドセットが異なるためです。

```python
# 旧コード（None チェックなし）
print(f"売上高: {record.revenue:,}")
print(f"営業CF: {record.operating_cf:,}")

# 新コード（None チェック必須）
if record.revenue is not None:
    print(f"売上高: {record.revenue:,.0f}")
if record.cf_operating is not None:
    print(f"営業CF: {record.cf_operating:,.0f}")
```

#### DuckDB スキーマの自動マイグレーション

`EdinetStorage` は初回アクセス時に既存テーブルのスキーマを自動検査し、以下を実行します:

1. **カラム名の変更**: `operating_cf` → `cf_operating` 等の自動リネーム
2. **不足カラムの追加**: 新フィールドに対応するカラムを `NULL` デフォルトで追加

手動のスキーマ変更は不要です。既存の DuckDB ファイルはそのまま使用できます。

---

## モジュール構成

```
market/edinet/
├── __init__.py          # パッケージエクスポート
├── client.py            # EdinetClient（10 エンドポイント、リトライ・ポライトディレイ付き）
├── constants.py         # 定数（BASE_URL、テーブル名、ランキング指標等）
├── errors.py            # 例外クラス（EdinetError 階層）
├── rate_limiter.py      # DailyRateLimiter（日次 API 制限管理、JSON 永続化）
├── storage.py           # EdinetStorage（DuckDB 8 テーブル管理）
├── syncer.py            # EdinetSyncer（6 フェーズ同期、チェックポイント再開）
├── types.py             # 型定義（EdinetConfig、データクラス群）
└── scripts/
    └── sync.py          # CLI スクリプト（--initial/--daily/--resume/--status/--company）
```

---

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `EDINET_DB_API_KEY` | EDINET DB API キー | なし（必須） |
| `EDINET_DB_PATH` | DuckDB ファイルパス | `get_db_path("duckdb", "edinet")` の返り値 |

`EDINET_DB_PATH` の優先順位:

1. `EdinetConfig(db_path=...)` で明示指定（最優先）
2. `EDINET_DB_PATH` 環境変数
3. `get_db_path("duckdb", "edinet")` のデフォルト値

---

## トラブルシューティング

### API キーエラー

```
ValueError: api_key must not be empty.
```

**解決方法:** 環境変数 `EDINET_DB_API_KEY` を設定するか、`EdinetConfig(api_key="...")` で直接指定してください。

### レート制限エラー

```
EdinetRateLimitError: Daily API call limit exceeded
```

**解決方法:**

- 翌日に実行するか、`EdinetSyncer.resume()` でチェックポイントから再開
- `DailyRateLimiter` で残り呼び出し数を事前確認
- Business プランへのアップグレードを検討（10,000件/日）

### 接続エラー（リトライ後も失敗）

```
EdinetAPIError: Request failed after 3 attempts
```

**解決方法:**

- ネットワーク接続を確認
- `RetryConfig(max_attempts=5, initial_delay=2.0)` でリトライ設定を強化

---

## 関連モジュール

- [market.fred](../fred/README.md) - FRED 経済指標データ取得
- [market.edgar](../../edgar/README.md) - SEC EDGAR 財務データ取得
- [database](../../database/README.md) - DuckDB/SQLite 接続ユーティリティ
