# market.industry

コンサルティングファームや投資銀行のウェブサイトから業界レポートをスクレイピングし、政府統計 API でデータを補完、競争優位性を評価するモジュール。

## 概要

このモジュールは、業界リサーチと競争優位性分析のための統合ツールキットを提供します。

**主な機能:**

- **業界レポート収集**: McKinsey・BCG・Goldman Sachs 等のウェブサイトから最新レポートを自動収集
- **2層フォールバック**: Tier 1（curl_cffi 直接 HTTP）→ Tier 2（Playwright ヘッドレスブラウザ）
- **政府統計 API**: BLS（雇用・賃金・生産性）と Census Bureau（国際貿易）からのデータ取得
- **PDF ダウンロード・パース**: SHA-256 重複排除付きダウンロード、PyMuPDF/trafilatura による本文抽出
- **ピアグループ分析**: プリセット設定 + yfinance 動的取得によるピアグループ定義
- **競争優位性分析**: dogma.md 12 ルール評価・モートスコアリング・ポーターの 5 フォース
- **定期実行スケジューリング**: APScheduler による週次自動収集

## インストール

このモジュールは `market` パッケージの一部です。

```bash
# リポジトリ全体の依存関係をインストール
uv sync --all-extras
```

## クイックスタート

### 5分で試せる基本的な使い方

```python
import asyncio
from market.industry import IndustryCollector, load_presets

# 1. プリセット設定を読み込む
config = load_presets()
print(f"設定済みセクター: {config.sector_names}")
# => ['Technology', 'Healthcare', 'Financials', ...]

# 2. Technology セクターの業界レポートを一括収集する
collector = IndustryCollector(sector="Technology")
stats = asyncio.run(collector.collect())

# 3. 収集結果を確認する
print(f"成功: {stats.success_count}/{stats.total_sources} ソース")
print(f"収集レポート数: {stats.total_reports}")
print(f"所要時間: {stats.duration_seconds:.1f}秒")
```

**出力例:**

```
設定済みセクター: ['Technology', 'Healthcare', 'Financials', ...]
成功: 9/11 ソース
収集レポート数: 47
所要時間: 85.3秒
```

---

## 業界レポート収集

### IndustryCollector: 全ソースの一括収集

コンサルティングファームと投資銀行のスクレイパーを統合的に実行するオーケストレーター。

```python
import asyncio
from market.industry import IndustryCollector

# セクター指定で全ソースを収集
collector = IndustryCollector(sector="Healthcare")
stats = asyncio.run(collector.collect())

for result in stats.results:
    status = "OK" if result.success else "FAILED"
    print(f"[{status}] {result.source}: {result.report_count}件 ({result.duration_seconds:.1f}s)")
```

**コンストラクタのパラメータ:**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `sector` | `str` | `"all"` | 対象セクター（例: `"Technology"`, `"Healthcare"`） |
| `ticker` | `str \| None` | `None` | ティッカー指定でセクターを自動判定 |
| `source` | `str \| None` | `None` | 特定ソースのみ実行（例: `"mckinsey"`, `"goldman"`） |
| `output_dir` | `Path \| None` | `None` | 保存先ディレクトリ（デフォルト: `data/raw/industry_reports`） |

---

## スクレイパー

### コンサルティングファームスクレイパー

8社のコンサルティングファームから業界レポートを収集します。

| クラス | 収集元 | URL |
|--------|--------|-----|
| `McKinseyScraper` | McKinsey Insights | `mckinsey.com/featured-insights` |
| `BCGScraper` | BCG Publications | `bcg.com/publications` |
| `DeloitteScraper` | Deloitte Insights | `deloitte.com/insights` |
| `PwCScraper` | PwC Strategy& | `strategyand.pwc.com` |
| `BainScraper` | Bain Insights | `bain.com/insights` |
| `AccentureScraper` | Accenture Insights | `accenture.com/us-en/insights` |
| `EYScraper` | EY Insights | `ey.com/en_us/insights` |
| `KPMGScraper` | KPMG Insights | `kpmg.com/us/en/insights.html` |

```python
import asyncio
from market.industry import McKinseyScraper

async def main():
    async with McKinseyScraper(sector="Technology") as scraper:
        result = await scraper.scrape()
        if result.success:
            print(f"McKinsey: {len(result.reports)} レポート取得")
            for report in result.reports[:3]:
                print(f"  - {report.title}")
                print(f"    {report.url}")
            # レポートを JSON ファイルとして保存
            paths = await scraper.save_reports(result.reports)
            print(f"保存先: {len(paths)} ファイル")

asyncio.run(main())
```

### 投資銀行スクレイパー

3社の投資銀行から業界レポートを収集します。

| クラス | 収集元 | URL |
|--------|--------|-----|
| `GoldmanSachsScraper` | Goldman Sachs Insights | `goldmansachs.com/insights` |
| `MorganStanleyScraper` | Morgan Stanley Ideas | `morganstanley.com/ideas` |
| `JPMorganScraper` | JP Morgan Research | `jpmorgan.com/insights/research` |

```python
import asyncio
from market.industry import GoldmanSachsScraper

async def main():
    async with GoldmanSachsScraper(sector="all") as scraper:
        result = await scraper.scrape()
        if result.success:
            for report in result.reports:
                print(f"{report.published_at.date()} | {report.title}")

asyncio.run(main())
```

### 2層フォールバックの仕組み

すべてのスクレイパーは以下の順序でフォールバックします:

1. **Tier 1 (curl_cffi)**: TLS フィンガープリント偽装による高速 HTTP リクエスト
2. **Tier 2 (Playwright)**: JavaScript レンダリングが必要なページ向けヘッドレスブラウザ

```python
from market.industry import ScrapingConfig, RetryConfig

# スクレイピング設定をカスタマイズ
config = ScrapingConfig(
    polite_delay=3.0,      # リクエスト間隔（秒）
    delay_jitter=1.5,      # ランダムな追加待機（秒）
    impersonate="chrome",  # TLS フィンガープリント
    timeout=45.0,          # タイムアウト（秒）
    headless=True,         # Playwright のヘッドレスモード
)
retry_config = RetryConfig(
    max_attempts=5,         # 最大リトライ回数
    initial_delay=1.0,      # 初回リトライ前の待機（秒）
    max_delay=30.0,         # 最大待機時間（秒）
    exponential_base=2.0,   # 指数バックオフの基数
    jitter=True,            # ランダムジッター
)

async with McKinseyScraper(sector="Technology", config=config, retry_config=retry_config) as scraper:
    result = await scraper.scrape()
```

---

## 政府統計 API

### BLSClient: 雇用・賃金・生産性データ

BLS (Bureau of Labor Statistics) Public Data API v2.0 を使用して、雇用統計・賃金・生産性データを取得します。

**事前準備: API キーの取得**

1. [BLS API キー登録ページ](https://data.bls.gov/registrationEngine/) にアクセス
2. 無料登録して API キーを取得
3. 環境変数に設定: `export BLS_API_KEY="your-key"`

**制限:** リクエストあたり最大 50 シリーズ、最大 20 年間、1日 500 クエリ

```python
import asyncio
from market.industry import BLSClient

async def main():
    async with BLSClient() as client:
        # 製造業の雇用者数を取得（2020年〜現在）
        response = await client.get_series(
            series_ids=["CES3133440001"],  # 製造業雇用
            start_year=2020,
            end_year=2025,
        )
        for series in response.series:
            print(f"シリーズ: {series.series_id}")
            print(f"データ件数: {len(series.data)}")
            latest = series.data[0]
            print(f"最新値: {latest.value} ({latest.period_name} {latest.year})")

asyncio.run(main())
```

**主要な BLS シリーズ ID:**

| シリーズ ID | 説明 |
|------------|------|
| `CES3133440001` | 製造業雇用者数 |
| `LNS14000000` | 失業率 |
| `CES0500000003` | 非農業部門平均時給 |
| `PRS85006092` | 非農業部門労働生産性 |

### CensusClient: 国際貿易データ

Census Bureau 国際貿易 API を使用して、輸出入データを取得します。

**事前準備: API キーの取得**

1. [Census Bureau API キー登録ページ](https://api.census.gov/data/key_signup.html) にアクセス
2. 無料登録して API キーを取得
3. 環境変数に設定: `export CENSUS_API_KEY="your-key"`

```python
import asyncio
from market.industry import CensusClient

async def main():
    async with CensusClient() as client:
        # 2025年1月の輸出データを HS 分類で取得
        response = await client.get_trade_data(
            flow="exports",          # "exports" または "imports"
            classification="hs",     # "hs", "naics", "enduse"
            year=2025,
            month=1,
        )
        print(f"レコード数: {len(response.data)}")
        print(f"総輸出額: ${response.total_value:,.0f}")
        for record in response.data[:5]:
            print(f"  {record.commodity_code}: ${record.value:,.0f} - {record.commodity_description}")

asyncio.run(main())
```

---

## PDF ダウンロード・パース

### PDFDownloader: SHA-256 重複排除付きダウンロード

PDF ファイルを非同期でダウンロードし、サイズ制限チェックと SHA-256 ハッシュによる重複排除を実施します。

```python
import asyncio
from pathlib import Path
from market.industry import PDFDownloader

async def main():
    downloader = PDFDownloader(
        download_dir=Path("data/raw/industry_reports/pdfs"),
        max_file_size=50 * 1024 * 1024,  # 50 MB 上限
        timeout=30.0,
    )

    result = await downloader.download("https://example.com/annual-report.pdf")
    if result.success:
        print(f"保存先: {result.file_path}")
        print(f"ファイルサイズ: {result.file_size:,} bytes")
        print(f"SHA-256: {result.content_hash}")
        print(f"重複: {result.is_duplicate}")
    else:
        print(f"エラー: {result.error_message}")

asyncio.run(main())
```

### ReportParser: PDF/HTML テキスト抽出

PyMuPDF（PDF）または trafilatura（HTML）を使用してレポートのテキストとメタデータを抽出します。

```python
from pathlib import Path
from market.industry import ReportParser

parser = ReportParser(min_text_length=100)

# PDF からテキスト抽出
pdf_result = parser.parse_pdf(Path("data/raw/industry_reports/pdfs/report.pdf"))
print(f"ページ数: {pdf_result.page_count}")
print(f"文字数: {len(pdf_result.text)}")
if pdf_result.metadata:
    print(f"タイトル: {pdf_result.metadata.title}")
    print(f"著者: {pdf_result.metadata.author}")

# HTML からテキスト抽出
html_result = parser.parse_html("<html><body>...</body></html>")
print(f"本文: {html_result.text[:200]}")
```

---

## ピアグループ分析

### get_peer_group: プリセット優先・動的フォールバック

```python
from market.industry import get_peer_group, load_presets

config = load_presets()

# 1. ティッカーからピアグループを取得（プリセット優先）
group = get_peer_group("NVDA", config)
if group:
    print(f"セクター: {group.sector}")
    print(f"サブセクター: {group.sub_sector}")
    print(f"ピア企業: {group.companies}")
```

### get_preset_peer_group: プリセットからの直接取得

```python
from market.industry import get_preset_peer_group, load_presets

config = load_presets()

# セクター名で直接取得
group = get_preset_peer_group("Technology", config)
if group:
    print(f"プリセット企業群: {group.companies}")
    # => ['NVDA', 'AMD', 'INTC', 'TSM', 'AVGO', 'MSFT', 'ORCL', 'CRM']
```

### get_dynamic_peer_group: yfinance からの動的取得

```python
from market.industry import get_dynamic_peer_group

# yfinance の Ticker.info からセクター・業種を動的に取得
group = get_dynamic_peer_group("AAPL")
if group:
    print(f"セクター: {group.sector}")       # => 'Technology'
    print(f"業種: {group.sub_sector}")       # => 'Consumer Electronics'
```

**3種の取得関数の使い分け:**

| 関数 | 動作 | 推奨用途 |
|------|------|---------|
| `get_peer_group` | プリセット優先、失敗時は動的 | 通常の使用（推奨） |
| `get_preset_peer_group` | プリセット設定のみ | プリセット管理された企業群が必要な場合 |
| `get_dynamic_peer_group` | yfinance から動的生成 | 任意のティッカーのセクター情報を取得する場合 |

---

## 競争優位性分析

### CompetitiveAnalyzer: dogma.md 12 ルール評価

analyst_YK の `dogma.md` に基づく 12 ルールで競争優位性の主張を定量的に評価します。

```python
from market.industry import (
    CompetitiveAnalyzer,
    AdvantageClaim,
    MoatType,
)

analyzer = CompetitiveAnalyzer()

# 評価する主張を定義
claims = [
    AdvantageClaim(
        claim="買収ターゲットの選定能力",
        evidence="買収基準の明確化、人員投入プロセス、バリュエーション規律",
        ticker="CHD",
        is_structural=True,       # 構造的能力か（結果ではなく）
        is_quantitative=True,     # 定量的裏付けがあるか
        has_competitor_comparison=True,  # 競合との比較があるか
        is_industry_common=False, # 業界共通の能力か
    ),
    AdvantageClaim(
        claim="ブランド力による価格決定力",
        evidence="プレミアム価格帯を維持",
        ticker="CHD",
        is_structural=True,
        is_quantitative=False,
        has_competitor_comparison=False,
        is_industry_common=False,
    ),
]

# 評価を実行
assessments = analyzer.evaluate_claims(claims)
for a in assessments:
    print(f"主張: {a.claim}")
    print(f"  確信度: {a.confidence.value}% ({a.confidence.name})")
    print(f"  モートタイプ: {a.moat_type.value}")

# モートスコアを集計
moat = analyzer.score_moat(assessments)
print(f"\n総合モートスコア: {moat.overall_score}/100")
print(f"モート強度: {moat.strength.value}")  # 'wide'(>=70) / 'narrow'(40-69) / 'none'(<40)
print(f"主要モートタイプ: {moat.dominant_moat.value}")
print(f"サマリー: {moat.summary}")
```

**確信度スケール (ConfidenceLevel):**

| 値 | 名前 | 意味 |
|----|------|------|
| 90 | `HIGHLY_CONVINCED` | 構造的優位性 + 明確な CAGR 接続 + 定量的証拠 |
| 70 | `MOSTLY_CONVINCED` | 合理的仮説 + 一定の証拠（競合比較またはデータ） |
| 50 | `SOMEWHAT_CONVINCED` | 方向性は認められるが証拠不足 |
| 30 | `NOT_CONVINCED` | 論理的飛躍・因果逆転・差別化不足 |
| 10 | `REJECTED` | 事実誤認・競争優位性に該当しない |

**dogma.md 12 ルール:**

| ルール | 名前 | 判定方法 |
|--------|------|---------|
| 1 | 能力・仕組み vs 結果・実績 | `is_structural` |
| 2 | 名詞属性 vs 動詞行動 | `is_structural` |
| 3 | 相対的優位性の要求 | `not is_industry_common` |
| 4 | 定量的裏付け | `is_quantitative` (+20%) |
| 5 | CAGR 接続の直接性・検証可能性 | 中立 |
| 6 | 構造的要素 vs 補完的要素 | `is_structural` |
| 7 | 純粋競合に対する差別化 | `has_competitor_comparison` (+15%) |
| 8 | 戦略 ≠ 優位性 | `is_structural` |
| 9 | 事実誤認の即却下 | 外部検証（中立） |
| 10 | ネガティブケースによる裏付け | 追加情報依存（中立） |
| 11 | 業界構造とポジションの合致 | 構造的+比較+定量的で +30% |
| 12 | 期初レポート主、四半期レビュー従 | コンテキスト依存（中立） |

### evaluate_porter_forces: ポーターの 5 フォース評価

```python
from market.industry import evaluate_porter_forces

industry_data = {
    "market_concentration": "low",      # 市場集中度（低=競争激化）
    "entry_barriers": "high",           # 参入障壁（高=脅威低）
    "substitute_availability": "low",   # 代替品の利用可能性（低=脅威低）
    "supplier_concentration": "medium", # サプライヤー集中度
    "buyer_concentration": "low",       # バイヤー集中度
}

assessment = evaluate_porter_forces(industry_data)
print(f"全体的な競争強度: {assessment.overall_intensity}")  # 'low' / 'medium' / 'high'
for force in assessment.forces:
    print(f"  {force.name}: {force.strength.value}")
    print(f"    {force.reasoning}")
```

---

## プリセット設定

### load_presets: セクター別設定の JSON 管理

業界リサーチのプリセット設定を `data/config/industry-research-presets.json` から読み込みます。

```python
from market.industry import load_presets, IndustryPresetsConfig
from pathlib import Path

# デフォルトパスから読み込む
config = load_presets()

print(f"バージョン: {config.version}")
print(f"セクター数: {len(config.presets)}")
print(f"セクター一覧: {config.sector_names}")

# 特定セクターのプリセットを取得
tech_preset = config.get_sector("Technology")
if tech_preset:
    print(f"サブセクター: {tech_preset.sub_sectors}")
    print(f"ピア企業: {tech_preset.peer_tickers}")
    print(f"データソース数: {len(tech_preset.sources)}")

# カスタムパスから読み込む
custom_config = load_presets(Path("custom/presets.json"))
```

**JSON 設定の構造:**

```json
{
  "version": "1.0",
  "presets": [
    {
      "sector": "Technology",
      "sub_sectors": ["Semiconductors", "Software_Infrastructure"],
      "sources": [
        {
          "name": "McKinsey Insights",
          "url": "https://mckinsey.com/featured-insights",
          "tier": "scraping",
          "difficulty": "medium",
          "enabled": true
        }
      ],
      "peer_tickers": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
      "peer_groups": [
        {
          "sub_sector": "Semiconductors",
          "companies": ["NVDA", "AMD", "INTC"],
          "description": "Major semiconductor manufacturers"
        }
      ],
      "scraping_queries": [
        {
          "query": "semiconductor industry outlook 2026",
          "target_sources": ["McKinsey", "BCG"],
          "sector_specific": true
        }
      ],
      "competitive_factors": [...],
      "industry_media": [...],
      "key_metrics": [...]
    }
  ]
}
```

---

## 定期実行スケジューリング

### IndustryScheduler: APScheduler 週次自動実行

APScheduler のクーロンスケジューラを使用して、業界レポート収集を週次で自動実行します。

```python
from market.industry import IndustryScheduler

# 毎週日曜日の午前0時に Technology セクターの全ソースを収集
scheduler = IndustryScheduler(
    sector="Technology",
    day_of_week="sun",  # 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
    hour=0,
    minute=0,
)

# ブロッキングモード（フォアグラウンドで実行）
scheduler.start(blocking=True)

# バックグラウンドモード
scheduler = IndustryScheduler(sector="Healthcare", day_of_week="sat", hour=3)
scheduler.start(blocking=False)
# ... 他の処理 ...
next_run = scheduler.get_next_run_time()
print(f"次回実行: {next_run}")
scheduler.stop()

# 前回の収集結果を確認
if scheduler.last_stats:
    print(f"最終収集: {scheduler.last_stats.total_reports}件")
```

---

## CLI 使用方法

```bash
# Technology セクターの全ソースから業界レポートを収集
uv run python -m market.industry.collect --sector Technology

# ティッカーからセクターを自動判定して収集
uv run python -m market.industry.collect --ticker AAPL

# 特定のソースのみ収集
uv run python -m market.industry.collect --source mckinsey
uv run python -m market.industry.collect --source goldman
uv run python -m market.industry.collect --source jpmorgan

# 出力先ディレクトリを指定
uv run python -m market.industry.collect --sector Healthcare --output-dir /data/reports

# 有効なソースキー一覧
# mckinsey, bcg, deloitte, pwc, bain, accenture, ey, kpmg,
# goldman, morgan_stanley, jpmorgan
```

---

## 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `BLS_API_KEY` | BLS Public Data API キー | なし（必須） |
| `CENSUS_API_KEY` | Census Bureau API キー | なし（必須） |

---

## API リファレンス

### IndustryCollector

業界レポート収集のメインオーケストレーター。

**コンストラクタ:**

```python
IndustryCollector(
    sector: str = "all",
    ticker: str | None = None,
    source: str | None = None,
    output_dir: Path | None = None,
)
```

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `collect()` | 全マッチソースから収集を実行 | `CollectionStats` |

### BaseScraper / ConsultingScraper / InvestmentBankScraper

**主なメソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `scrape()` | スクレイピングを実行 | `ScrapingResult` |
| `parse_html(html)` | HTML を解析してレポートを抽出 | `list[IndustryReport]` |
| `save_reports(reports)` | レポートを JSON ファイルとして保存 | `list[Path]` |

### BLSClient

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `get_series(series_ids, start_year, end_year)` | BLS 時系列データを取得 | `BLSResponse` |
| `get_series_as_reports(series_ids, sector)` | BLS データを IndustryReport 形式で取得 | `list[IndustryReport]` |

### CensusClient

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `get_trade_data(flow, classification, year, month)` | 国際貿易データを取得 | `CensusTradeResponse` |
| `get_trade_as_reports(flow, classification, year, month, sector)` | 貿易データを IndustryReport 形式で取得 | `list[IndustryReport]` |

### PDFDownloader

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `download(url)` | PDF をダウンロードして保存 | `DownloadResult` |
| `has_hash(content_hash)` | ハッシュが登録済みか確認 | `bool` |
| `register_hash(content_hash, file_path)` | ハッシュを登録 | `None` |

### ReportParser

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `parse_pdf(pdf_path)` | PDF からテキストとメタデータを抽出 | `ParsedContent` |
| `parse_html(html_content)` | HTML からテキストとメタデータを抽出 | `ParsedContent` |

### CompetitiveAnalyzer

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `evaluate_claims(claims)` | 複数の主張を評価 | `list[AdvantageAssessment]` |
| `score_moat(assessments)` | 評価結果からモートスコアを集計 | `MoatScore` |
| `evaluate_porter_forces(industry_data)` | ポーターの 5 フォースを評価 | `PorterForcesAssessment` |

### IndustryScheduler

**コンストラクタ:**

```python
IndustryScheduler(
    sector: str = "all",
    source: str | None = None,
    day_of_week: str = "sun",
    hour: int = 0,
    minute: int = 0,
)
```

**メソッド:**

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `start(blocking=True)` | スケジューラを開始 | `None` |
| `stop()` | スケジューラを停止 | `None` |
| `run_batch()` | 一回分の収集バッチを即時実行 | `CollectionStats` |
| `get_next_run_time()` | 次回実行時刻を取得 | `datetime \| None` |

---

## 型定義

```python
from market.industry import (
    # データモデル
    IndustryReport,         # 業界レポート 1 件
    ScrapingResult,         # スクレイピング操作の結果
    PeerGroup,              # ピアグループ定義
    DownloadResult,         # PDF ダウンロード結果
    ParsedContent,          # パース済みコンテンツ
    ReportMetadata,         # レポートのメタデータ

    # 設定モデル
    ScrapingConfig,         # スクレイピング設定
    RetryConfig,            # リトライ設定
    SourceConfig,           # データソース設定
    IndustryPreset,         # セクター別プリセット
    IndustryPresetsConfig,  # プリセット全体設定

    # 収集結果
    CollectionResult,       # ソース別収集結果
    CollectionStats,        # 収集バッチ全体の統計

    # 競争優位性分析
    AdvantageClaim,         # 評価対象の主張
    AdvantageAssessment,    # 主張の評価結果
    DogmaRuleResult,        # 個別ルールの評価結果
    MoatScore,              # モートスコア集計
    PorterForce,            # ポーター 5 フォースの 1 力評価
    PorterForcesAssessment, # 5 フォース全体評価

    # 列挙型
    SourceTier,             # API / SCRAPING / MEDIA
    ConfidenceLevel,        # 10 / 30 / 50 / 70 / 90
    MoatType,               # BRAND_POWER / SWITCHING_COST / etc.
    MoatStrength,           # WIDE / NARROW / NONE
    PorterForceStrength,    # HIGH / MEDIUM / LOW
)
```

---

## モジュール構成

```
market/industry/
├── __init__.py                    # パッケージエクスポート（公開 API 全定義）
├── __main__.py                    # CLI エントリポイント
├── types.py                       # 型定義（Pydantic モデル・列挙型）
├── config.py                      # プリセット設定ローダー
├── collector.py                   # IndustryCollector（CLI オーケストレーター）
├── peer_groups.py                 # ピアグループ取得関数
├── competitive_analysis.py        # 競争優位性分析（dogma.md / ポーター 5 フォース）
├── scheduler.py                   # APScheduler 週次スケジューラ
├── scrapers/
│   ├── __init__.py
│   ├── base.py                    # BaseScraper（2層フォールバック基底クラス）
│   ├── consulting.py              # McKinsey / BCG / Deloitte / PwC / Bain 等
│   └── investment_bank.py        # Goldman Sachs / Morgan Stanley / JP Morgan
├── api_clients/
│   ├── __init__.py
│   ├── bls.py                     # BLSClient（雇用統計 API v2.0）
│   └── census.py                  # CensusClient（国際貿易 API）
└── downloaders/
    ├── __init__.py
    ├── pdf_downloader.py          # PDFDownloader（SHA-256 重複排除）
    └── report_parser.py           # ReportParser（PyMuPDF / trafilatura）
```

**収集データの保存先:**

```
data/raw/industry_reports/
├── mckinsey/        # McKinsey レポート JSON
├── bcg/             # BCG レポート JSON
├── deloitte/        # Deloitte レポート JSON
├── pwc/             # PwC レポート JSON
├── bain/            # Bain レポート JSON
├── accenture/       # Accenture レポート JSON
├── ey/              # EY レポート JSON
├── kpmg/            # KPMG レポート JSON
├── goldman/         # Goldman Sachs レポート JSON
├── morgan_stanley/  # Morgan Stanley レポート JSON
├── jpmorgan/        # JP Morgan レポート JSON
├── bls/             # BLS API キャッシュ JSON
├── census/          # Census API キャッシュ JSON
└── pdfs/            # ダウンロード済み PDF ファイル
```

---

## 関連モジュール

| モジュール | 関係 |
|-----------|------|
| `market.fred` | 類似の政府 API クライアントパターン（キャッシュ・リトライ） |
| `market.etfcom` | スクレイピングパターンの参照実装（2層フォールバック） |
| `market.nasdaq` | curl_cffi セッションの参照実装 |
| `edgar` | SEC Filings 抽出（競争優位性分析の入力データ） |
| `analyze` | 市場データ分析（ピアグループ分析の後処理） |
