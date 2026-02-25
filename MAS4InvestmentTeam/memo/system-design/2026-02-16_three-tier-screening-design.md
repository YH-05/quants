# 3段階スクリーニング設計メモ

## 背景・課題

S&P 500（~500銘柄）のユニバース全てについてLLMベースの個別調査を行うのはコストが高い。使えるデータソースが限定されている（10-K, 10-Q, Transcript、マーケットデータ）前提で、コスト効率の良いスクリーニングで~100銘柄に絞り、そこから精査して20-30銘柄のポートフォリオを構築する方法を設計する。

## データソースの特性

| ソース | データ種別 | LLM必要？ | コスト |
|--------|-----------|-----------|--------|
| yfinance | 株価・リターン・時価総額 | No | 無料（API） |
| SEC EDGAR XBRL | 構造化財務データ（ROE, EPS等） | No | 無料（API 10req/s） |
| SEC 10-K/10-Q テキスト | 非構造化テキスト（MD&A等） | **Yes** | 高い |
| Earnings Transcript | 非構造化テキスト | **Yes** | 高い |

**重要な洞察**: SEC EDGAR の XBRL データ（`get_financials`, `get_key_metrics`, `get_company_facts`）は構造化済みなのでPythonで直接処理可能。LLMコールなしで財務スクリーニングができる。

---

## 3段階スクリーニング

```
S&P 500 (500銘柄)
    │
    │  Tier 1: Price-Based Filter (Python + yfinance)
    │  コスト: ほぼゼロ、所要: ~10秒
    ↓
  ~250銘柄
    │
    │  Tier 2: Financial Quality Filter (Python + SEC XBRL)
    │  コスト: ほぼゼロ、所要: ~30秒
    ↓
  ~80-100銘柄
    │
    │  Tier 3: LLM Deep Analysis (Agent Teams)
    │  コスト: $0.50-1.50/銘柄、所要: ~30-60秒/銘柄
    ↓
  ~20-30銘柄（ポートフォリオ）
```

### Tier 1: Price-Based Filter（500 → ~250）

yfinance の価格データのみ使用。LLMコールなし。

```python
tier1_filters = {
    # 1. 流動性フィルタ（非流動的な銘柄を除外）
    "min_avg_daily_volume_20d": 500_000,      # 直近20日平均出来高
    "min_trading_days_ratio": 0.95,            # 直近1年の取引日充足率

    # 2. モメンタムスコア（最も実証的根拠の強いファクター）
    "momentum_12_1": "top_60%",                # 12ヶ月リターン（直近1ヶ月除外）
    # ※ 直近1ヶ月を除外する理由: 短期リバーサル効果の排除

    # 3. ボラティリティフィルタ（極端なリスクを排除）
    "max_annualized_vol": 0.60,                # 年率ボラティリティ60%以下
    "min_annualized_vol": 0.10,                # 極端に低いボラも除外（データ異常の可能性）

    # 4. サイズフィルタ（S&P500内なので大きな絞り込みにはならない）
    "min_market_cap_usd": 5_000_000_000,       # 時価総額50億ドル以上
}
```

**除外される銘柄の例**:
- 出来高が極端に少ない銘柄（流動性リスク）
- 直近12ヶ月で大幅下落中の銘柄（モメンタム負け組）
- ボラティリティが極端に高い銘柄（破綻リスク・投機的）

### Tier 2: Financial Quality Filter（250 → ~80-100）

SEC EDGAR の XBRL 構造化データを使用。LLMコールなし。

```python
tier2_factors = {
    # --- 収益性（Quality） --- ウェイト: 30%
    "roe": {                          # 自己資本利益率
        "source": "XBRL: us-gaap/ReturnOnEquity or 計算(NetIncome/Equity)",
        "filter": "> 0.08",          # ROE 8%以上
        "score": "z-score",
    },
    "operating_margin": {             # 営業利益率
        "source": "XBRL: us-gaap/OperatingIncomeLoss / Revenue",
        "filter": "> 0.05",          # 営業利益率5%以上
        "score": "z-score",
    },
    "gross_margin_stability": {       # 粗利率の安定性（直近4四半期の標準偏差）
        "source": "XBRL: 4四半期分のGrossProfit/Revenue",
        "filter": "std < 0.10",      # 粗利率の変動が10%未満
        "score": "inverse_z-score",  # 安定しているほど高スコア
    },

    # --- 成長性（Growth） --- ウェイト: 25%
    "revenue_growth_yoy": {           # 売上成長率（YoY）
        "source": "XBRL: Revenue の前年同期比",
        "filter": "> -0.10",         # 売上10%以上の減少を除外
        "score": "z-score",
    },
    "eps_growth_yoy": {               # EPS成長率（YoY）
        "source": "XBRL: EarningsPerShareBasic の前年同期比",
        "filter": "None",            # フィルタなし（スコアのみ）
        "score": "z-score",
    },

    # --- 財務健全性（Safety） --- ウェイト: 20%
    "debt_to_equity": {               # 負債資本比率
        "source": "XBRL: us-gaap/DebtToEquityRatio or 計算",
        "filter": "< 3.0",           # D/E 3倍以下（金融除く）
        "score": "inverse_z-score",  # 低いほど高スコア
    },
    "interest_coverage": {            # インタレストカバレッジ
        "source": "XBRL: OperatingIncome / InterestExpense",
        "filter": "> 2.0",           # 2倍以上
        "score": "z-score",
    },
    "fcf_positive": {                 # フリーキャッシュフローが正
        "source": "XBRL: CashFromOperations - CapEx",
        "filter": "> 0",             # FCF正
        "score": "binary",
    },

    # --- バリュエーション（Value） --- ウェイト: 25%
    "earnings_yield": {               # 益回り（PERの逆数）
        "source": "XBRL EPS / yfinance 株価",
        "filter": "> 0",             # 黒字企業のみ
        "score": "z-score",          # 高いほど割安
    },
    "fcf_yield": {                    # FCF利回り
        "source": "XBRL FCF / yfinance 時価総額",
        "filter": "None",
        "score": "z-score",
    },
}

# 複合スコア
composite_weights = {
    "quality": 0.30,    # 収益性
    "growth": 0.25,     # 成長性
    "safety": 0.20,     # 財務健全性
    "value": 0.25,      # バリュエーション
}

# → 複合スコア上位80-100銘柄を Tier 3 に進める
```

**XBRL データ取得の実装イメージ**:

```python
# SEC EDGAR XBRL は構造化済み → Pythonで直接処理可能
# 500銘柄 × 10req/sec = ~50秒で全銘柄の財務データ取得

async def fetch_xbrl_metrics(ticker: str, cutoff_date: date) -> dict:
    """SEC EDGAR XBRLから財務指標を取得（LLM不要）"""
    # get_company_facts or get_financials で構造化データ取得
    # filing_date < cutoff_date でフィルタ（PoiT遵守）
    ...
```

### Tier 3: LLM Deep Analysis（80-100 → 20-30）

ここで初めてLLMを使用。Fundamental Analyst + Fund Manager が各銘柄を評価。

```
80-100銘柄 × ($0.50-1.50/銘柄) = $40-150/リバランス回
```

**Tier 3 で LLM が付加価値を出すポイント**:

| 分析項目 | XBRL では困難な理由 | LLM の付加価値 |
|----------|-------------------|---------------|
| MD&A の文脈理解 | 非構造化テキスト | 経営陣のトーン・戦略変化を読み取る |
| リスク要因の評価 | Item 1A は自然言語 | 競争環境・規制リスクの重要度判定 |
| 会計の質 | 数値だけでは判断困難 | 異常な会計変更・aggressive accounting の検出 |
| セクター横断比較 | 企業固有の文脈が必要 | 同業他社対比での強み・弱みの判定 |

---

## セクター別の考慮事項

金融セクターは一般的な財務指標が異なるため、セクター別の閾値が必要：

```python
sector_adjustments = {
    "Financials": {
        "debt_to_equity": {"filter": None},  # 金融はD/E比率フィルタ不適用
        "replace_with": {
            "tier1_capital_ratio": "> 0.10",  # 代わりに自己資本比率
            "net_interest_margin": "> 0.02",
        }
    },
    "Utilities": {
        "debt_to_equity": {"filter": "< 2.5"},  # 閾値を緩和
        "revenue_growth_yoy": {"filter": "> -0.05"},  # 成長期待を低く
    },
    "Real Estate": {
        "replace_with": {
            "ffo_per_share": "XBRL: FundsFromOperations",  # FFOベースで評価
        }
    },
}
```

---

## コスト比較

| 段階 | 処理 | LLMコスト | API/計算コスト | 所要時間 |
|------|------|-----------|---------------|---------|
| Tier 1 | yfinance価格データ | $0 | ~10秒 | ~10秒 |
| Tier 2 | SEC XBRL財務データ | $0 | ~50秒 | ~50秒 |
| Tier 3 | LLM分析（80-100銘柄） | $40-150 | - | ~40-100分 |
| **合計/リバランス** | | **$40-150** | | **~1-2時間** |
| **フル期間（80四半期）** | | **$3,200-12,000** | | **~80-160時間** |

**当初の設計（全500銘柄をLLM分析）との比較**:

| | 当初案 | 3段階スクリーニング案 |
|--|--------|---------------------|
| LLM分析対象 | ~500銘柄 | ~80-100銘柄 |
| コスト/リバランス | $250-750 | $40-150 |
| フル期間コスト | $20,000-60,000 | $3,200-12,000 |
| 所要時間/リバランス | ~4-8時間 | ~1-2時間 |

---

## 未検討事項

- Tier 2 の各ファクターウェイトの最適化（バックテストで検証すべき）
- XBRL データの歴史的カバレッジ（2006年頃は XBRL 普及前のためフォールバック戦略が必要）
- セクター分類の時系列変化（GICS分類の変更）への対応
- failure_patterns.json（Postmortem）との統合方法
