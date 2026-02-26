# 却下パターンC-T: 因果関係の混同・拡大解釈（トランスクリプト版）

## 種別: 却下パターン
## 確信度: 20-30%

## パターン定義

因果関係の飛躍、混同、拡大解釈を含む広い概念。以下の2類型がある:

1. **因果関係の飛躍**: 3段階以上の推論チェーンで各段階の裏付けがない
2. **戦略→優位性の混同を含む因果の拡大解釈**: 戦略的施策が優位性として主張される場合（**パターンF-T参照**）、結果への影響度を過大評価するような原因特定

決算トランスクリプトでは、CEOやCFOが因果関係を説明する際に中間ステップを省略する傾向がある。経営陣が「〜だから〜になる」と語っても、各段階の裏付けを確認する必要がある。

> **v1.0修正（2026-02-26）:** アナリスト検証により、旧定義「因果関係の飛躍」から拡張。MNST#5例は本質的にはパターンF-T（戦略→優位性の混同）に内包されることが確認された。

## 具体例

### MNST#5: 低所得→コンビニ購買→粘着力（30%）
- KY: 「飛躍的な解釈との印象」
- **問題**: 「低所得 → コンビニでの定期購買率が高い → 粘着力高い」の各ステップに裏付けがない
- **v1.0補足**: 本例は低所得者向けの「戦略」が顧客粘着力という「優位性」につながることへの批判であり、本質的にはパターンF-T（戦略→優位性の混同）に内包される

### COST思いやり経営CAGR: 従業員満足→顧客サービス→既存店成長（20%）
- KY: 「左程顧客サービスが重要と思われない倉庫型店舗では飛躍しすぎ」
- **問題**: 因果チェーンの中間ステップ（従業員満足→顧客サービスの質→売上）が倉庫型店舗の文脈で成立しない

### COST思いやり経営CAGR: 退職率低下→営業レバレッジ+0.25%（20%）
- KY: 「増収効果に大きく依存する営業レバレッジ+0.25%への接続はやや飛躍しすぎ」
- **問題**: 退職率低下→コスト削減→営業レバレッジの各ステップの定量的裏付けがない

## 経営陣発言での検出パターン（トランスクリプト適応）

### 因果関係の飛躍を含む発言

**パターンC-T1: 従業員満足度→株主価値への直結**
> "By investing in our employees through competitive wages, flexible work arrangements, and career development programs, we create a more engaged workforce. Engaged employees deliver better customer experiences. Better customer experiences drive retention and referrals. That virtuous cycle ultimately drives superior long-term shareholder value."

- **検出**: 従業員投資→エンゲージメント→顧客体験→リテンション→株主価値という4-5ステップの因果チェーン。各段階に定量データなし（「engaged employees deliver better CX」の裏付けは？「better CX drives retention」のデータは？）。飛躍パターン（20-30%）。

**パターンC-T2: 技術投資→競争優位→市場支配**
> "Our $500 million annual investment in R&D will enable us to maintain our technology leadership. Technology leadership translates to premium pricing power. Premium pricing power combined with our scale will allow us to capture the majority of value creation in our industry."

- **検出**: R&D投資→技術リーダーシップ→プライシングパワー→市場支配という3-4ステップ。「technology leadership translates to premium pricing」の実証データなし。飛躍パターン（20-30%）。

**パターンC-T3: ESG活動→財務成果への直結**
> "Our sustainability initiatives have significantly reduced our carbon footprint and water usage. As ESG becomes more important to institutional investors, our strong ESG profile will lower our cost of capital, which will directly improve our returns and competitive positioning."

- **検出**: ESG改善→機関投資家評価→資本コスト低減→リターン改善→競争力という多段階。「ESG profile→lower cost of capital」の定量的裏付けなし（低い資本コストの差は？bpで何bp？）。飛躍パターン（20-30%）。

## KYのルール

因果関係の混同や拡大解釈を広く検出する。具体的には:
- 因果チェーンが3段階以上で各段階に裏付けがない場合は「飛躍」
- 戦略と優位性の混同に加え、結果への影響度を過大評価するような原因特定も該当（パターンF-Tとの重複に注意）

## 飛躍の判定基準

| 因果チェーンの長さ | 評価 | 条件 |
|------------------|------|------|
| 1-2ステップ | 高評価可能 | 各ステップが検証可能 |
| 3ステップ | 慎重 | 各ステップに裏付けが必要 |
| 4ステップ以上 | 低評価 | ほぼ確実に「飛躍」と判断される |

## 検出のチェックポイント

- 因果チェーンは何段階あるか？
- 各段階に定量的データの裏付けがあるか？
- 中間ステップは業界の文脈で成立するか？
- 代替的な因果経路が無視されていないか？
- CEOが "will"、"should"、"ultimately"で接続する場合は飛躍の可能性が高い
