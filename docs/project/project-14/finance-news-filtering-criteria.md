# 金融ニュースフィルタリング基準

**作成日**: 2026-01-15
**ステータス**: Draft
**関連Issue**: [#150](https://github.com/YH-05/quants/issues/150)

## 概要

RSSフィードから取得したニュース記事の中から金融・投資関連のニュースを自動抽出するためのフィルタリング基準を定義する。

## 1. 金融関連キーワードリスト

### 1.1 市場・取引関連

#### 株式市場
- **日本語**: 株価、株式、上場、株主、株高、株安、相場、指数、日経平均、TOPIX、マザーズ、東証、証券取引所
- **英語**: stock, equity, share, IPO, index, Nikkei, TOPIX, exchange

#### 為替市場
- **日本語**: 為替、円高、円安、ドル円、ユーロ、FX、外国為替、通貨
- **英語**: forex, FX, currency, exchange rate, yen, dollar, euro

#### 債券市場
- **日本語**: 債券、国債、社債、利回り、償還
- **英語**: bond, treasury, yield, maturity

#### コモディティ
- **日本語**: 金、原油、商品、先物
- **英語**: gold, oil, commodity, futures

### 1.2 金融政策・経済指標

#### 金融政策
- **日本語**: 金利、政策金利、量的緩和、金融緩和、金融引き締め、日銀、FRB、ECB、中央銀行
- **英語**: interest rate, monetary policy, quantitative easing, QE, Fed, central bank

#### 経済指標
- **日本語**: GDP、消費者物価指数、CPI、失業率、景気動向指数、鉱工業生産、貿易収支、経常収支
- **英語**: GDP, CPI, unemployment, PMI, trade balance

### 1.3 企業財務・投資

#### 企業決算
- **日本語**: 決算、業績、売上高、営業利益、純利益、EPS、ROE、ROA、増収、減益、上方修正、下方修正
- **英語**: earnings, revenue, profit, EPS, ROE, ROA, guidance

#### 投資関連
- **日本語**: 投資、投資家、ファンド、資産運用、ポートフォリオ、分散投資、リスク管理、リターン
- **英語**: investment, investor, fund, asset management, portfolio, diversification

#### M&A・企業活動
- **日本語**: M&A、買収、合併、提携、資本参加、株式取得
- **英語**: M&A, acquisition, merger, alliance, stake

### 1.4 投資商品

- **日本語**: 投資信託、ETF、REIT、仮想通貨、暗号資産、ビットコイン、デリバティブ、オプション
- **英語**: mutual fund, ETF, REIT, cryptocurrency, Bitcoin, derivatives, options

### 1.5 金融機関・規制

#### 金融機関
- **日本語**: 銀行、証券、保険、フィンテック、決済
- **英語**: bank, securities, insurance, fintech, payment

#### 規制・制度
- **日本語**: 金融庁、規制、コンプライアンス、インサイダー取引、情報開示、NISA、iDeCo、税制
- **英語**: regulation, compliance, disclosure, NISA, tax

## 2. 除外条件

### 2.1 除外カテゴリ

以下のカテゴリに該当し、かつ金融関連キーワードを含まないニュースは除外する。

#### スポーツ
- **キーワード**: サッカー、野球、バスケ、テニス、オリンピック、ワールドカップ、優勝、試合
- **例外**: スポーツビジネス、放映権、スポンサー契約など金融関連の話題は含む

#### エンターテイメント
- **キーワード**: 映画、音楽、ドラマ、アニメ、芸能人、俳優、歌手、アイドル
- **例外**: 興行収入、配信ビジネス、著作権収益など金融関連の話題は含む

#### 政治（金融無関係）
- **キーワード**: 選挙、内閣改造、外交、防衛、安全保障（経済政策を含まない場合）
- **例外**: 経済政策、財政政策、税制改正など金融に影響を与える政治ニュースは含む

#### 社会・事件
- **キーワード**: 事故、災害、犯罪、裁判（金融犯罪を除く）
- **例外**: 経済への影響が大きい災害、金融犯罪、詐欺事件は含む

#### 科学・技術（一般）
- **キーワード**: 宇宙、医療、生物学、物理学（ビジネス応用なし）
- **例外**: テクノロジー企業、AI/IoTビジネス、研究開発投資など金融関連の話題は含む

### 2.2 除外ロジック

1. **単純除外**: 除外キーワードのみを含み、金融キーワードを含まない → 除外
2. **混合判定**: 除外キーワードと金融キーワードの両方を含む → 含む（金融関連として扱う）
3. **カテゴリフィルタ**: RSSフィードのカテゴリが明確に非金融である → 除外

## 3. 信頼性基準

### 3.1 情報源の分類

#### Tier 1（高信頼性）
- 大手メディア: 日経新聞、ロイター、ブルームバーグ、Wall Street Journal
- 公式発表: 企業IR、金融庁、日銀、財務省
- 評価: 即座に採用

#### Tier 2（中信頼性）
- 一般メディア: 朝日新聞、読売新聞、毎日新聞、NHK
- 専門メディア: 東洋経済、ダイヤモンド、Forbes
- 評価: 金融キーワードの強度で判定

#### Tier 3（要検証）
- 個人ブログ、まとめサイト
- 評価: 情報源の確認が必要、優先度低

### 3.2 信頼性スコアリング

```
信頼性スコア = 情報源Tier × キーワードマッチ度
- Tier 1: 3点
- Tier 2: 2点
- Tier 3: 1点

キーワードマッチ度 = マッチしたキーワード数 / 総文字数
```

### 3.3 採用基準

- **信頼性スコア ≥ 5**: 自動採用
- **信頼性スコア 2-4**: 要確認
- **信頼性スコア < 2**: 除外

## 4. 重複排除ロジック

### 4.1 重複の定義

同一ニュースと判定する条件（いずれかに該当）:

1. **URL完全一致**: `link` フィールドが完全一致
2. **タイトル類似度**: 編集距離（Levenshtein distance）で類似度 ≥ 85%
3. **時間+タイトル**: 公開時刻が1時間以内 かつ タイトルの主要キーワードが一致

### 4.2 重複判定アルゴリズム

```python
def is_duplicate(item1: FeedItem, item2: FeedItem) -> bool:
    # 1. URL完全一致
    if item1.link == item2.link:
        return True

    # 2. タイトル類似度
    similarity = calculate_similarity(item1.title, item2.title)
    if similarity >= 0.85:
        return True

    # 3. 時間+タイトルキーワード
    if is_within_hour(item1.published, item2.published):
        if has_common_keywords(item1.title, item2.title, threshold=0.7):
            return True

    return False
```

### 4.3 重複解決戦略

重複が検出された場合の優先順位:

1. **情報源の信頼性**: Tier 1 > Tier 2 > Tier 3
2. **公開時刻**: より新しい方を採用
3. **コンテンツ充実度**: `summary` または `content` が長い方を採用

## 5. フィルタリングフロー

### 5.1 全体フロー

```
[RSS Feed]
    ↓
[1. キーワードマッチング] → 金融関連キーワードを含むか？
    ↓ Yes
[2. 除外判定] → 除外カテゴリか？
    ↓ No
[3. 重複チェック] → 既存ニュースと重複？
    ↓ No
[4. 信頼性スコアリング] → スコア ≥ 2？
    ↓ Yes
[5. 採用]
    ↓
[GitHub Project に投稿]
```

### 5.2 実装方針

#### Phase 1: 基本フィルタリング（必須）
- 金融キーワードマッチング（title, summary, content）
- URL重複チェック
- 除外キーワードによる簡易フィルタリング

#### Phase 2: 高度フィルタリング（推奨）
- タイトル類似度計算
- 信頼性スコアリング
- 時間ベース重複検出

#### Phase 3: 最適化（将来）
- 機械学習ベースの分類
- 感情分析・トーン検出
- トピッククラスタリング

## 6. 設定ファイル形式

### 6.1 フィルタリング設定（JSON形式）

```json
{
  "version": "1.0",
  "keywords": {
    "include": {
      "market": ["株価", "為替", "金利", "stock", "forex"],
      "policy": ["金融政策", "GDP", "CPI", "monetary policy"],
      "corporate": ["決算", "業績", "M&A", "earnings"],
      "investment": ["投資", "ファンド", "investment", "fund"]
    },
    "exclude": {
      "sports": ["サッカー", "野球", "オリンピック"],
      "entertainment": ["映画", "音楽", "ドラマ"],
      "politics": ["選挙", "内閣改造"],
      "general": ["事故", "災害"]
    }
  },
  "sources": {
    "tier1": ["nikkei.com", "reuters.com", "bloomberg.com"],
    "tier2": ["asahi.com", "yomiuri.co.jp", "toyokeizai.net"],
    "tier3": []
  },
  "filtering": {
    "min_keyword_matches": 1,
    "title_similarity_threshold": 0.85,
    "time_window_hours": 1,
    "min_reliability_score": 2
  }
}
```

### 6.2 配置場所

```
data/config/finance-news-filter.json
```

## 7. テスト戦略

### 7.1 単体テスト

- キーワードマッチング関数
- 除外判定ロジック
- 重複検出アルゴリズム
- 信頼性スコアリング

### 7.2 統合テスト

- 実際のRSSフィードを使用したフィルタリング
- エンドツーエンドのフロー確認

### 7.3 テストケース

#### 正常系
- 金融キーワードを含むニュースが正しく抽出される
- 除外キーワードのみのニュースが除外される
- 重複ニュースが1件のみ採用される

#### 異常系
- キーワードが存在しない場合
- 情報源不明の場合
- タイトルや本文が空の場合

#### 境界値
- キーワード数が閾値ギリギリ
- 類似度が閾値ギリギリ
- 時間差が1時間ちょうど

## 8. 運用・メンテナンス

### 8.1 キーワード更新

- **頻度**: 四半期ごと
- **方法**: 新しい金融トピック、流行語の追加
- **承認**: プロジェクトオーナーによるレビュー

### 8.2 精度モニタリング

- **メトリクス**:
  - 適合率（Precision）: 採用されたニュースのうち実際に金融関連だった割合
  - 再現率（Recall）: 全金融ニュースのうち採用された割合
  - F1スコア

- **改善サイクル**:
  1. 誤検出/見逃しの分析
  2. キーワードリストの更新
  3. 閾値の調整
  4. 再テスト

## 9. 参考情報

### 9.1 関連ドキュメント

- `docs/project/financial-news-rss-collector.md` - プロジェクト計画書
- `src/rss/README.md` - RSSパッケージドキュメント
- `src/rss/services/feed_reader.py` - キーワード検索実装

### 9.2 外部リソース

- [情報検索の基礎](https://nlp.stanford.edu/IR-book/)
- [テキスト類似度計算手法](https://en.wikipedia.org/wiki/Levenshtein_distance)

---

**最終更新**: 2026-01-15
