# ヘルスケア規制トラッカー実装計画

## 概要

米国ヘルスケアセクターの規制・制度変更を自動追跡し、株価パフォーマンスとの相関を分析するシステムを構築する。

### 目的

1. **リスク早期検知**: 規制発表を株価に織り込まれる前にキャッチ
2. **影響分析**: 過去の規制イベントと株価の相関を定量化
3. **投資判断支援**: 既存ポジションのリスク管理と新規投資判断

### 対象サブセクター

| サブセクター | 代表的銘柄 | 主な規制リスク |
|--------------|-----------|----------------|
| 製薬（大手） | JNJ, PFE, MRK, ABBV, LLY | 薬価交渉(IRA)、特許クリフ、FDA承認 |
| バイオテック | AMGN, GILD, BIIB, VRTX | FDA承認、臨床試験規制、バイオシミラー |
| 医療機器 | MDT, ABT, BSX, SYK, ISRG | FDA 510(k)/PMA、リコール、診療報酬 |
| 医療保険 | UNH, ELV, CI, HUM, CVS | Medicare Advantage、ACA、MLR規制 |
| 病院・医療サービス | HCA, THC, UHS, SGRY | 診療報酬改定、人員配置規制、340B |
| PBM・薬局 | CVS, WBA, CI | FTC調査、スプレッド規制、DIR fee |

---

## Phase 1: データ収集基盤（2-3週間）

### 1.1 Federal Register API連携

**優先度: 最高** - 構造化されたAPIで規制案・最終規則を取得可能

#### API仕様

```
Base URL: https://www.federalregister.gov/api/v1/
認証: 不要（レート制限あり: 1000 req/hour）
フォーマット: JSON
```

#### 主要エンドポイント

| エンドポイント | 用途 | パラメータ例 |
|----------------|------|--------------|
| `/documents` | ドキュメント検索 | `agencies[]=health-and-human-services` |
| `/documents/{number}` | 個別ドキュメント取得 | - |
| `/public-inspection-documents` | 公開前ドキュメント | 先行情報として重要 |

#### 検索条件

```python
# ヘルスケア関連機関
HEALTHCARE_AGENCIES = [
    "health-and-human-services",
    "food-and-drug-administration",
    "centers-for-medicare-medicaid-services",
    "federal-trade-commission",  # PBM関連
]

# ドキュメントタイプ
DOCUMENT_TYPES = [
    "RULE",           # 最終規則（最重要）
    "PRORULE",        # 規則案（先行指標）
    "NOTICE",         # 通知
    "PRESDOCU",       # 大統領令
]

# キーワード（サブセクター別）
KEYWORDS = {
    "pharma": ["drug pricing", "medicare negotiation", "prescription drug", "biosimilar"],
    "device": ["medical device", "510(k)", "premarket approval", "recall"],
    "insurance": ["medicare advantage", "medicaid", "health insurance", "ACA"],
    "hospital": ["reimbursement", "diagnosis-related group", "340B", "staffing"],
    "pbm": ["pharmacy benefit", "rebate", "spread pricing", "DIR fee"],
}
```

#### 実装タスク

| タスク | 詳細 | 成果物 |
|--------|------|--------|
| 1.1.1 | APIクライアント実装 | `src/regulatory/clients/federal_register.py` |
| 1.1.2 | レスポンスモデル定義 | `src/regulatory/models/federal_register.py` |
| 1.1.3 | 検索クエリビルダー | 機関・キーワード・日付範囲の組み合わせ |
| 1.1.4 | 差分取得ロジック | 前回取得以降の新規ドキュメントのみ取得 |
| 1.1.5 | キャッシュ機構 | SQLite/DuckDBへの保存 |

#### サンプルコード

```python
"""Federal Register APIクライアント"""
from dataclasses import dataclass
from datetime import date
from typing import Literal
import httpx

@dataclass
class FederalRegisterDocument:
    """Federal Registerドキュメント"""
    document_number: str
    title: str
    abstract: str | None
    publication_date: date
    document_type: Literal["RULE", "PRORULE", "NOTICE", "PRESDOCU"]
    agencies: list[str]
    topics: list[str]
    html_url: str
    pdf_url: str | None
    effective_on: date | None  # 規則の発効日
    comments_close_on: date | None  # コメント締切日

class FederalRegisterClient:
    """Federal Register API クライアント"""

    BASE_URL = "https://www.federalregister.gov/api/v1"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30.0)

    def search_documents(
        self,
        agencies: list[str] | None = None,
        document_types: list[str] | None = None,
        keywords: list[str] | None = None,
        publication_date_gte: date | None = None,
        publication_date_lte: date | None = None,
        per_page: int = 100,
    ) -> list[FederalRegisterDocument]:
        """ドキュメント検索"""
        params = {
            "per_page": per_page,
            "order": "newest",
        }

        if agencies:
            params["conditions[agencies][]"] = agencies
        if document_types:
            params["conditions[type][]"] = document_types
        if keywords:
            params["conditions[term]"] = " OR ".join(keywords)
        if publication_date_gte:
            params["conditions[publication_date][gte]"] = publication_date_gte.isoformat()
        if publication_date_lte:
            params["conditions[publication_date][lte]"] = publication_date_lte.isoformat()

        response = self.client.get(f"{self.BASE_URL}/documents", params=params)
        response.raise_for_status()

        return [self._parse_document(doc) for doc in response.json()["results"]]

    def _parse_document(self, data: dict) -> FederalRegisterDocument:
        """APIレスポンスをモデルに変換"""
        return FederalRegisterDocument(
            document_number=data["document_number"],
            title=data["title"],
            abstract=data.get("abstract"),
            publication_date=date.fromisoformat(data["publication_date"]),
            document_type=data["type"],
            agencies=[a["name"] for a in data.get("agencies", [])],
            topics=data.get("topics", []),
            html_url=data["html_url"],
            pdf_url=data.get("pdf_url"),
            effective_on=date.fromisoformat(data["effective_on"]) if data.get("effective_on") else None,
            comments_close_on=date.fromisoformat(data["comments_close_on"]) if data.get("comments_close_on") else None,
        )
```

---

### 1.2 FDA データソース連携

#### 1.2.1 FDA Press Announcements (RSS)

```
RSS URL: https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds
主要フィード:
- Drug Approvals: https://www.fda.gov/feeds/drugs-news-events-drug-approvals.rss
- Medical Devices: https://www.fda.gov/feeds/medical-devices-news-events.rss
- Press Announcements: https://www.fda.gov/feeds/press-announcements.rss
```

#### 1.2.2 openFDA API

```
Base URL: https://api.fda.gov
認証: APIキー推奨（レート制限緩和）
ドキュメント: https://open.fda.gov/apis/
```

| エンドポイント | 用途 |
|----------------|------|
| `/drug/event` | 有害事象レポート（安全性シグナル） |
| `/drug/enforcement` | リコール・市場撤退 |
| `/device/enforcement` | 医療機器リコール |
| `/drug/label` | ラベル変更（警告追加など） |

#### 実装タスク

| タスク | 詳細 | 成果物 |
|--------|------|--------|
| 1.2.1 | FDA RSSフィード追加 | `data/raw/rss/fda_feeds.json` |
| 1.2.2 | openFDA APIクライアント | `src/regulatory/clients/openfda.py` |
| 1.2.3 | リコール監視 | Drug/Device enforcementの定期取得 |
| 1.2.4 | 承認・却下イベント抽出 | Press Announcementsからのパース |

---

### 1.3 CMS データソース連携

#### CMSの主要データソース

| ソース | URL | 内容 | 更新頻度 |
|--------|-----|------|----------|
| CMS Newsroom | https://www.cms.gov/newsroom | プレスリリース | 随時 |
| Medicare FFS Rates | https://www.cms.gov/medicare/payment | 診療報酬 | 年次 |
| MA Rate Announcement | CMS.gov | Medicare Advantage支払い率 | 年次（2月） |
| IRA Negotiation | https://www.cms.gov/inflation-reduction-act-and-medicare | 薬価交渉 | 随時 |

#### 実装タスク

| タスク | 詳細 | 成果物 |
|--------|------|--------|
| 1.3.1 | CMS Newsroomスクレイパー | `src/regulatory/scrapers/cms_newsroom.py` |
| 1.3.2 | IRA交渉対象薬モニタリング | 対象薬リストの自動更新 |
| 1.3.3 | MA Rate Announcementパーサー | 年次発表のアラート |

---

### 1.4 Congress/法案トラッキング

#### GovTrack API（推奨）

```
Base URL: https://www.govtrack.us/api/v2/
認証: 不要
ドキュメント: https://www.govtrack.us/developers/api
```

#### 監視対象の法案カテゴリ

```python
HEALTHCARE_BILL_KEYWORDS = [
    "medicare",
    "medicaid",
    "drug pricing",
    "pharmaceutical",
    "health insurance",
    "hospital",
    "medical device",
    "FDA",
    "340B",
    "PBM",
    "pharmacy benefit",
]

# 重要委員会
RELEVANT_COMMITTEES = [
    "Senate Health, Education, Labor, and Pensions",
    "Senate Finance",
    "House Energy and Commerce",
    "House Ways and Means",
]
```

#### 実装タスク

| タスク | 詳細 | 成果物 |
|--------|------|--------|
| 1.4.1 | GovTrack APIクライアント | `src/regulatory/clients/govtrack.py` |
| 1.4.2 | 法案フィルタリング | ヘルスケア関連法案の自動抽出 |
| 1.4.3 | 進捗追跡 | 委員会通過、本会議採決などのマイルストーン |

---

### 1.5 業界専門メディアRSS

既存の`rss`パッケージに追加するフィード：

```python
HEALTHCARE_RSS_FEEDS = [
    # 政策・規制特化
    {
        "name": "STAT News - Policy",
        "url": "https://www.statnews.com/category/policy/feed/",
        "category": "healthcare_policy",
    },
    {
        "name": "Health Affairs Blog",
        "url": "https://www.healthaffairs.org/action/showFeed?type=etoc&feed=rss&jc=hlthaff",
        "category": "healthcare_policy",
    },
    # 製薬・バイオ
    {
        "name": "Endpoints News",
        "url": "https://endpts.com/feed/",
        "category": "pharma_biotech",
    },
    {
        "name": "FiercePharma",
        "url": "https://www.fiercepharma.com/rss/xml",
        "category": "pharma",
    },
    {
        "name": "FierceBiotech",
        "url": "https://www.fiercebiotech.com/rss/xml",
        "category": "biotech",
    },
    # 医療機器
    {
        "name": "MedTech Dive",
        "url": "https://www.medtechdive.com/feeds/news/",
        "category": "device",
    },
    # 保険・病院
    {
        "name": "FierceHealthcare",
        "url": "https://www.fiercehealthcare.com/rss/xml",
        "category": "insurance_hospital",
    },
    {
        "name": "Healthcare Dive",
        "url": "https://www.healthcaredive.com/feeds/news/",
        "category": "insurance_hospital",
    },
    # PBM
    {
        "name": "Drug Channels",
        "url": "https://www.drugchannels.net/feeds/posts/default?alt=rss",
        "category": "pbm",
    },
]
```

---

## Phase 2: イベント分類・保存（1-2週間）

### 2.1 データモデル設計

#### ER図

```
┌─────────────────────┐      ┌─────────────────────┐
│  regulatory_events  │      │    event_impacts    │
├─────────────────────┤      ├─────────────────────┤
│ id (PK)             │      │ id (PK)             │
│ source              │      │ event_id (FK)       │
│ source_id           │──────│ subsector           │
│ title               │      │ impact_score        │
│ summary             │      │ affected_tickers    │
│ published_at        │      └─────────────────────┘
│ effective_at        │
│ document_type       │      ┌─────────────────────┐
│ agencies            │      │   event_keywords    │
│ url                 │      ├─────────────────────┤
│ raw_content         │      │ id (PK)             │
│ importance_score    │──────│ event_id (FK)       │
│ created_at          │      │ keyword             │
│ updated_at          │      │ relevance_score     │
└─────────────────────┘      └─────────────────────┘
         │
         │
         ▼
┌─────────────────────┐
│   price_reactions   │
├─────────────────────┤
│ id (PK)             │
│ event_id (FK)       │
│ ticker              │
│ event_date          │
│ car_1d              │  # 1日CAR
│ car_3d              │  # 3日CAR
│ car_5d              │  # 5日CAR
│ car_10d             │  # 10日CAR
│ volume_ratio        │  # 出来高比率
│ created_at          │
└─────────────────────┘
```

#### Pydanticモデル

```python
"""規制イベントモデル"""
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field

class EventSource(str, Enum):
    """イベントソース"""
    FEDERAL_REGISTER = "federal_register"
    FDA = "fda"
    CMS = "cms"
    CONGRESS = "congress"
    FTC = "ftc"
    NEWS = "news"

class DocumentType(str, Enum):
    """ドキュメントタイプ"""
    FINAL_RULE = "final_rule"
    PROPOSED_RULE = "proposed_rule"
    NOTICE = "notice"
    GUIDANCE = "guidance"
    PRESS_RELEASE = "press_release"
    BILL = "bill"
    EXECUTIVE_ORDER = "executive_order"

class Subsector(str, Enum):
    """ヘルスケアサブセクター"""
    PHARMA = "pharma"
    BIOTECH = "biotech"
    DEVICE = "device"
    INSURANCE = "insurance"
    HOSPITAL = "hospital"
    PBM = "pbm"

class ImpactDirection(str, Enum):
    """影響の方向"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class RegulatoryEvent(BaseModel):
    """規制イベント"""
    id: str = Field(..., description="一意識別子")
    source: EventSource
    source_id: str = Field(..., description="ソース側のID")
    title: str
    summary: str | None = None
    published_at: datetime
    effective_at: date | None = None
    document_type: DocumentType
    agencies: list[str] = Field(default_factory=list)
    url: str
    importance_score: float = Field(ge=0, le=1, description="重要度スコア 0-1")

class EventImpact(BaseModel):
    """イベントの影響分析"""
    event_id: str
    subsector: Subsector
    impact_direction: ImpactDirection
    impact_score: float = Field(ge=-1, le=1, description="影響度 -1(ネガティブ)〜+1(ポジティブ)")
    affected_tickers: list[str] = Field(default_factory=list)
    rationale: str = Field(..., description="影響判断の根拠")

class PriceReaction(BaseModel):
    """株価反応"""
    event_id: str
    ticker: str
    event_date: date
    car_1d: float = Field(..., description="1日累積異常リターン")
    car_3d: float = Field(..., description="3日累積異常リターン")
    car_5d: float = Field(..., description="5日累積異常リターン")
    car_10d: float = Field(..., description="10日累積異常リターン")
    volume_ratio: float = Field(..., description="平均出来高比")
```

---

### 2.2 重要度スコアリング

#### スコアリングロジック

```python
"""イベント重要度スコアリング"""
from dataclasses import dataclass

@dataclass
class ImportanceFactors:
    """重要度判定要素"""
    document_type_weight: float  # ドキュメントタイプによる重み
    agency_weight: float         # 機関による重み
    keyword_match_score: float   # キーワードマッチスコア
    market_cap_exposure: float   # 影響を受ける時価総額
    recency_factor: float        # 直近性（発効日までの期間）

def calculate_importance_score(event: RegulatoryEvent) -> float:
    """
    重要度スコアを計算（0-1）

    スコアリング基準:
    1. ドキュメントタイプ
       - Final Rule: 1.0
       - Proposed Rule: 0.7
       - Notice/Guidance: 0.4
       - Press Release: 0.3

    2. 発行機関
       - CMS (Medicare/Medicaid): 1.0
       - FDA: 0.9
       - FTC: 0.8
       - HHS: 0.7

    3. キーワードマッチ
       - "price", "reimbursement", "payment": 高
       - "approval", "rejection", "recall": 高
       - "guidance", "comment": 中

    4. 市場インパクト推定
       - 影響を受ける銘柄の時価総額合計
    """
    # 実装詳細は省略
    pass

# ドキュメントタイプ重み
DOCUMENT_TYPE_WEIGHTS = {
    DocumentType.FINAL_RULE: 1.0,
    DocumentType.PROPOSED_RULE: 0.7,
    DocumentType.EXECUTIVE_ORDER: 0.9,
    DocumentType.NOTICE: 0.4,
    DocumentType.GUIDANCE: 0.5,
    DocumentType.PRESS_RELEASE: 0.3,
    DocumentType.BILL: 0.6,  # 成立確率による調整が必要
}

# 高影響キーワード
HIGH_IMPACT_KEYWORDS = [
    "final rule",
    "price negotiation",
    "reimbursement rate",
    "approval",
    "rejection",
    "recall",
    "warning letter",
    "consent decree",
    "investigation",
    "penalty",
    "settlement",
]
```

---

### 2.3 サブセクター自動分類

```python
"""サブセクター分類器"""
import re
from collections import defaultdict

class SubsectorClassifier:
    """テキストからサブセクターを分類"""

    PATTERNS = {
        Subsector.PHARMA: [
            r"drug pricing",
            r"prescription drug",
            r"pharmaceutical",
            r"medicare part d",
            r"inflation reduction act",
            r"negotiat",
        ],
        Subsector.BIOTECH: [
            r"biologic",
            r"biosimilar",
            r"gene therapy",
            r"cell therapy",
            r"orphan drug",
        ],
        Subsector.DEVICE: [
            r"medical device",
            r"510\(k\)",
            r"premarket approval",
            r"PMA",
            r"device recall",
        ],
        Subsector.INSURANCE: [
            r"medicare advantage",
            r"medicaid",
            r"health insurance",
            r"ACA",
            r"affordable care act",
            r"MLR",
            r"medical loss ratio",
        ],
        Subsector.HOSPITAL: [
            r"hospital",
            r"DRG",
            r"diagnosis.related group",
            r"inpatient",
            r"outpatient",
            r"340B",
            r"staffing",
        ],
        Subsector.PBM: [
            r"PBM",
            r"pharmacy benefit",
            r"rebate",
            r"spread pricing",
            r"DIR fee",
            r"formulary",
        ],
    }

    def classify(self, text: str) -> list[tuple[Subsector, float]]:
        """
        テキストからサブセクターを分類

        Returns
        -------
        list of (Subsector, confidence_score)
        """
        text_lower = text.lower()
        scores = defaultdict(float)

        for subsector, patterns in self.PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                scores[subsector] += len(matches) * 0.2

        # 正規化
        total = sum(scores.values()) or 1
        results = [(s, min(score / total, 1.0)) for s, score in scores.items() if score > 0]

        return sorted(results, key=lambda x: x[1], reverse=True)
```

---

## Phase 3: 株価データとの紐付け（1-2週間）

### 3.1 対象銘柄リスト

```python
"""ヘルスケアセクター銘柄リスト"""

HEALTHCARE_TICKERS = {
    Subsector.PHARMA: [
        "JNJ",   # Johnson & Johnson
        "PFE",   # Pfizer
        "MRK",   # Merck
        "ABBV",  # AbbVie
        "LLY",   # Eli Lilly
        "BMY",   # Bristol-Myers Squibb
        "AZN",   # AstraZeneca (ADR)
        "NVS",   # Novartis (ADR)
        "GSK",   # GSK (ADR)
        "SNY",   # Sanofi (ADR)
    ],
    Subsector.BIOTECH: [
        "AMGN",  # Amgen
        "GILD",  # Gilead Sciences
        "VRTX",  # Vertex Pharmaceuticals
        "REGN",  # Regeneron
        "BIIB",  # Biogen
        "MRNA",  # Moderna
        "ALNY",  # Alnylam
        "SGEN",  # Seagen
    ],
    Subsector.DEVICE: [
        "MDT",   # Medtronic
        "ABT",   # Abbott Laboratories
        "SYK",   # Stryker
        "BSX",   # Boston Scientific
        "ISRG",  # Intuitive Surgical
        "EW",    # Edwards Lifesciences
        "DXCM",  # DexCom
        "ZBH",   # Zimmer Biomet
    ],
    Subsector.INSURANCE: [
        "UNH",   # UnitedHealth
        "ELV",   # Elevance Health
        "CI",    # Cigna
        "HUM",   # Humana
        "CNC",   # Centene
        "MOH",   # Molina Healthcare
    ],
    Subsector.HOSPITAL: [
        "HCA",   # HCA Healthcare
        "THC",   # Tenet Healthcare
        "UHS",   # Universal Health Services
        "SGRY",  # Surgery Partners
        "ACHC",  # Acadia Healthcare
    ],
    Subsector.PBM: [
        "CVS",   # CVS Health (PBM + Pharmacy + Insurance)
        "WBA",   # Walgreens Boots Alliance
        "CI",    # Cigna (Express Scripts)
        "UNH",   # UnitedHealth (OptumRx)
    ],
}

# サブセクターETF
SUBSECTOR_ETFS = {
    "XLV": "Healthcare Select Sector SPDR",  # 全体
    "IBB": "iShares Biotechnology ETF",      # バイオ
    "IHI": "iShares U.S. Medical Devices ETF",  # 医療機器
    "XHS": "SPDR S&P Health Care Services ETF",  # サービス
    "ARKG": "ARK Genomic Revolution ETF",    # ゲノム
}
```

---

### 3.2 イベントスタディ分析

```python
"""イベントスタディ分析"""
from dataclasses import dataclass
from datetime import date, timedelta
import numpy as np
import pandas as pd
from scipy import stats

@dataclass
class EventStudyResult:
    """イベントスタディ結果"""
    ticker: str
    event_date: date
    car: dict[str, float]  # {"1d": 0.02, "3d": 0.05, ...}
    t_stats: dict[str, float]
    p_values: dict[str, float]
    abnormal_volume: float
    significant: bool

class EventStudyAnalyzer:
    """イベントスタディ分析器"""

    def __init__(
        self,
        estimation_window: int = 120,  # 推定ウィンドウ（日）
        gap: int = 10,                  # イベント前のギャップ
        event_windows: list[int] = None,
    ) -> None:
        self.estimation_window = estimation_window
        self.gap = gap
        self.event_windows = event_windows or [1, 3, 5, 10]

    def analyze(
        self,
        ticker: str,
        event_date: date,
        prices: pd.DataFrame,
        benchmark: pd.DataFrame,
    ) -> EventStudyResult:
        """
        単一イベントのイベントスタディ

        Parameters
        ----------
        ticker : 銘柄コード
        event_date : イベント日
        prices : 株価データ（Date, Close列）
        benchmark : ベンチマーク（S&P500等）

        Returns
        -------
        EventStudyResult
        """
        # 1. リターン計算
        stock_returns = prices["Close"].pct_change()
        market_returns = benchmark["Close"].pct_change()

        # 2. 推定ウィンドウでベータ推定（市場モデル）
        est_start = event_date - timedelta(days=self.estimation_window + self.gap)
        est_end = event_date - timedelta(days=self.gap)

        est_stock = stock_returns[est_start:est_end]
        est_market = market_returns[est_start:est_end]

        # OLS: R_i = alpha + beta * R_m + epsilon
        X = np.column_stack([np.ones(len(est_market)), est_market.values])
        y = est_stock.values
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        alpha, market_beta = beta[0], beta[1]

        # 3. イベントウィンドウで異常リターン計算
        car = {}
        t_stats = {}
        p_values = {}

        for window in self.event_windows:
            window_end = event_date + timedelta(days=window)

            actual = stock_returns[event_date:window_end].sum()
            expected = alpha * window + market_beta * market_returns[event_date:window_end].sum()

            ar = actual - expected
            car[f"{window}d"] = ar

            # t統計量（簡易版）
            residual_std = np.std(est_stock - (alpha + market_beta * est_market))
            t_stat = ar / (residual_std * np.sqrt(window))
            t_stats[f"{window}d"] = t_stat
            p_values[f"{window}d"] = 2 * (1 - stats.t.cdf(abs(t_stat), len(est_stock) - 2))

        # 4. 出来高分析
        avg_volume = prices["Volume"][est_start:est_end].mean()
        event_volume = prices["Volume"][event_date:event_date + timedelta(days=3)].mean()
        abnormal_volume = event_volume / avg_volume if avg_volume > 0 else 1.0

        # 5. 有意性判定（5%水準）
        significant = any(p < 0.05 for p in p_values.values())

        return EventStudyResult(
            ticker=ticker,
            event_date=event_date,
            car=car,
            t_stats=t_stats,
            p_values=p_values,
            abnormal_volume=abnormal_volume,
            significant=significant,
        )

    def analyze_portfolio(
        self,
        tickers: list[str],
        event_date: date,
    ) -> dict[str, EventStudyResult]:
        """複数銘柄の一括分析"""
        # 実装省略
        pass
```

---

### 3.3 相関分析

```python
"""規制イベントと株価の相関分析"""

class RegulatoryCorrelationAnalyzer:
    """規制イベントと株価パフォーマンスの相関分析"""

    def __init__(self, events_db: str, prices_fetcher) -> None:
        self.events_db = events_db
        self.prices = prices_fetcher

    def build_event_matrix(
        self,
        start_date: date,
        end_date: date,
        subsectors: list[Subsector] | None = None,
    ) -> pd.DataFrame:
        """
        イベント×銘柄の影響マトリクス作成

        Returns
        -------
        DataFrame with columns:
        - event_id, event_date, event_type, subsector
        - {ticker}_car_5d for each ticker
        """
        pass

    def calculate_cumulative_impact(
        self,
        subsector: Subsector,
        period: str = "2Y",
    ) -> dict:
        """
        期間累積の規制インパクト

        Returns
        -------
        {
            "total_events": 45,
            "negative_events": 30,
            "positive_events": 15,
            "cumulative_car": -0.15,  # 累積異常リターン
            "most_impactful": [...]
        }
        """
        pass

    def detect_lead_lag(
        self,
        event_id: str,
        ticker: str,
        window: int = 20,
    ) -> dict:
        """
        リード・ラグ関係の検出
        （発表前の織り込み度合い）

        Returns
        -------
        {
            "pre_event_car": 0.02,  # 発表前5日のCAR
            "post_event_car": 0.03,
            "leak_detected": True,
            "pre_event_volume_spike": True,
        }
        """
        pass
```

---

## Phase 4: アラート・レポート（1週間）

### 4.1 アラートシステム

```python
"""規制イベントアラート"""
from enum import Enum
from pydantic import BaseModel

class AlertPriority(str, Enum):
    CRITICAL = "critical"  # 最終規則、重大な政策変更
    HIGH = "high"          # 規則案、重要な発表
    MEDIUM = "medium"      # ガイダンス、通知
    LOW = "low"            # 参考情報

class RegulatoryAlert(BaseModel):
    """規制アラート"""
    priority: AlertPriority
    event: RegulatoryEvent
    affected_subsectors: list[Subsector]
    affected_tickers: list[str]
    estimated_impact: str
    action_required: str | None

class AlertConfig(BaseModel):
    """アラート設定"""
    enabled_subsectors: list[Subsector]
    min_priority: AlertPriority = AlertPriority.MEDIUM
    watched_tickers: list[str] = []
    notification_channels: list[str] = ["slack", "email"]

# アラート条件
ALERT_TRIGGERS = {
    AlertPriority.CRITICAL: [
        "final rule",
        "effective immediately",
        "price reduction",
        "recall class I",
        "consent decree",
    ],
    AlertPriority.HIGH: [
        "proposed rule",
        "comment period",
        "warning letter",
        "investigation",
        "negotiation",
    ],
}
```

### 4.2 週次レポート

```python
"""週次規制サマリーレポート"""

class WeeklyRegulatoryReport:
    """週次規制レポート生成"""

    def generate(self, week_start: date) -> str:
        """
        週次レポート生成

        セクション:
        1. 今週の重要イベントサマリー
        2. サブセクター別影響
        3. 来週の注目イベント（コメント締切、発効日など）
        4. 株価反応分析
        5. 監視推奨事項
        """
        pass
```

### 4.3 GitHub Project連携

既存の`news`パッケージのパターンを踏襲：

```python
"""GitHub Project への規制イベント投稿"""

class RegulatoryEventPublisher:
    """規制イベントをGitHub Issueとして投稿"""

    def __init__(
        self,
        project_number: int = 16,  # 規制トラッカー専用Project
        repo: str = "YH-05/quants",
    ) -> None:
        self.project_number = project_number
        self.repo = repo

    def create_issue(self, event: RegulatoryEvent, impact: EventImpact) -> str:
        """
        Issue作成

        タイトル: [{subsector}] {event.title}
        本文:
        - 概要
        - ソース: {url}
        - 発効日: {effective_at}
        - 影響度: {impact_score}
        - 影響銘柄: {tickers}
        """
        pass
```

---

## Phase 5: 既存リポジトリへの統合（1-2週間）

### 5.1 パッケージ構成

```
src/
├── regulatory/                    # 新規パッケージ
│   ├── __init__.py
│   ├── README.md
│   ├── clients/                   # APIクライアント
│   │   ├── __init__.py
│   │   ├── federal_register.py
│   │   ├── openfda.py
│   │   ├── govtrack.py
│   │   └── cms.py
│   ├── scrapers/                  # スクレイパー
│   │   ├── __init__.py
│   │   └── cms_newsroom.py
│   ├── models/                    # データモデル
│   │   ├── __init__.py
│   │   ├── events.py
│   │   └── impacts.py
│   ├── analyzers/                 # 分析
│   │   ├── __init__.py
│   │   ├── event_study.py
│   │   ├── correlation.py
│   │   └── classifier.py
│   ├── alerts/                    # アラート
│   │   ├── __init__.py
│   │   └── notifier.py
│   └── utils/
│       ├── __init__.py
│       └── tickers.py
│
├── rss/                           # 既存パッケージ（拡張）
│   └── feeds/
│       └── healthcare.json        # ヘルスケアRSSフィード定義
│
└── news/                          # 既存パッケージ（拡張）
    └── publishers/
        └── regulatory.py          # 規制イベント投稿
```

### 5.2 依存関係

```
database (既存)
    ↓
regulatory (新規)
    ├── market (既存) - 株価データ取得
    ├── rss (既存) - RSSフィード
    └── news (既存) - GitHub投稿
```

### 5.3 コマンド追加

```markdown
# .claude/commands/track-healthcare-regulatory.md

規制イベントの収集・分析を実行

## 使用方法
/track-healthcare-regulatory [--collect] [--analyze] [--report]

## オプション
- --collect: 新規イベント収集
- --analyze: 株価相関分析
- --report: 週次レポート生成
```

---

## 実装スケジュール

| Week | Phase | タスク | 成果物 |
|------|-------|--------|--------|
| 1 | 1.1 | Federal Register API PoC | APIクライアント動作確認 |
| 2 | 1.2-1.4 | FDA/CMS/Congress連携 | データ収集基盤 |
| 3 | 1.5, 2.1 | RSSフィード追加、DBモデル | イベントDB |
| 4 | 2.2-2.3 | スコアリング・分類 | 自動分類システム |
| 5 | 3.1-3.2 | イベントスタディ実装 | 分析エンジン |
| 6 | 3.3, 4.1 | 相関分析、アラート | 分析レポート |
| 7 | 4.2-4.3 | レポート・GitHub連携 | 自動化パイプライン |
| 8 | 5.1-5.3 | リポジトリ統合 | 本番運用開始 |

---

## 直近2年の主要イベント分析（初期検証用）

### 検証すべきイベント一覧

| 日付 | イベント | 影響セクター | 検証ポイント |
|------|----------|--------------|--------------|
| 2022/08/16 | **IRA成立** | 製薬 | PFE, MRK, ABBV等の反応 |
| 2023/08/29 | IRA交渉対象薬10品目発表 | 製薬 | Eliquis(BMS/PFE), Jardiance(LLY)等 |
| 2023/01 | MA Rate Announcement 2024 | 保険 | UNH, HUM, ELV |
| 2023/04 | FTC PBM調査開始 | PBM | CVS, CI |
| 2024/01 | MA Rate Announcement 2025 | 保険 | 前年比較 |
| 2024 | 340B訴訟判決 | 製薬・病院 | 双方への影響 |
| 2024 | GLP-1保険適用議論 | 製薬・保険 | LLY, NVO, UNH |

### 初期分析コマンド（手動実行用）

```python
# 直近2年のXLVパフォーマンス vs S&P500
import yfinance as yf
import pandas as pd

xlv = yf.download("XLV", start="2023-01-01", end="2025-01-29")
spy = yf.download("SPY", start="2023-01-01", end="2025-01-29")

xlv_return = (xlv["Close"][-1] / xlv["Close"][0] - 1) * 100
spy_return = (spy["Close"][-1] / spy["Close"][0] - 1) * 100

print(f"XLV 2年リターン: {xlv_return:.1f}%")
print(f"SPY 2年リターン: {spy_return:.1f}%")
print(f"相対パフォーマンス: {xlv_return - spy_return:.1f}%")
```

---

## 次のアクション

1. **Week 1**: Federal Register APIのPoC実装
   - `src/regulatory/clients/federal_register.py` 作成
   - 直近1ヶ月のヘルスケア関連ドキュメント取得テスト

2. **並行作業**: 直近2年の主要イベントと株価の相関を手動分析
   - IRA成立日前後のXLV, 個別銘柄のチャート確認
   - イベントスタディ分析の検証データとして使用

---

## 参考リンク

- [Federal Register API Documentation](https://www.federalregister.gov/developers/documentation/api/v1)
- [openFDA API](https://open.fda.gov/apis/)
- [GovTrack API](https://www.govtrack.us/developers/api)
- [CMS Data](https://data.cms.gov/)
- [Kaiser Family Foundation](https://www.kff.org/)
