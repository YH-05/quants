# YAML フロントマター テンプレート

各 KB ファイルの先頭に追加する YAML フロントマターの標準テンプレート。

---

## KB1: 評価ルール（Rules）

```yaml
---
id: rule_XX                              # ルール番号（例: rule_01）
title: "ルールタイトル"                    # ルールの正式名称
version: "1.0"                           # セマンティックバージョニング
kb: KB1                                  # ナレッジベース区分
type: rule                               # ファイル種別
category: "優位性の定義|裏付けの質"        # ルールカテゴリ
created: "YYYY-MM-DD"                    # 初版作成日
updated: "YYYY-MM-DD"                    # 最終更新日
---
```

### カテゴリ一覧

| カテゴリ | 該当ルール |
|---------|-----------|
| 優位性の定義 | rule_01, rule_02, rule_06, rule_08 |
| 裏付けの質 | rule_04, rule_07, rule_10, rule_11 |

---

## KB2: 判定パターン（Patterns）

```yaml
---
id: pattern_X                            # パターンID（例: pattern_A, pattern_I）
title: "パターンタイトル"                  # パターンの正式名称
version: "1.0"                           # セマンティックバージョニング
kb: KB2                                  # ナレッジベース区分
type: pattern                            # ファイル種別
pattern_type: rejection|high_rating      # 却下パターン or 高評価パターン
confidence_range: "XX-YY%"               # 確信度レンジ
created: "YYYY-MM-DD"                    # 初版作成日
updated: "YYYY-MM-DD"                    # 最終更新日
---
```

### パターン種別

| 種別 | ID範囲 | 確信度レンジ |
|------|--------|-------------|
| 却下パターン（rejection） | A〜G | 10〜50% |
| 高評価パターン（high_rating） | I〜V | 50〜90% |

---

## KB3: Few-shot 例（Fewshots）

```yaml
---
id: fewshot_XXXX                         # 銘柄ティッカー（例: fewshot_CHD）
title: "企業名"                           # 企業正式名称
ticker: XXXX                             # ティッカーシンボル
version: "1.0"                           # セマンティックバージョニング
kb: KB3                                  # ナレッジベース区分
type: fewshot                            # ファイル種別
avg_score: XX                            # 平均優位性スコア（%）
created: "YYYY-MM-DD"                    # 初版作成日
updated: "YYYY-MM-DD"                    # 最終更新日
---
```

---

## 統合ファイル（Consolidated）

```yaml
---
id: kbX_consolidated                     # 統合ファイルID
title: "KBX タイトル"                     # 統合ファイル名
version: "1.0"                           # セマンティックバージョニング
kb: KBX                                  # ナレッジベース区分
type: consolidated                       # ファイル種別
entry_count: X                           # 収録エントリ数
created: "YYYY-MM-DD"                    # 初版作成日
updated: "YYYY-MM-DD"                    # 最終更新日
sources:                                 # 収録元ファイル一覧
  - filename1.md
  - filename2.md
---
```

---

## バージョニング規約

| 変更種別 | バージョン変更 | 例 |
|---------|---------------|-----|
| 初版作成 | 1.0 | 新規ルール追加 |
| 軽微な修正（誤字、表現改善） | 1.0 → 1.1 | 文言修正 |
| 内容の追加・補足 | 1.0 → 1.1 | 具体例の追加 |
| 定義の変更・修正 | 1.0 → 2.0 | ルール定義の本質的変更 |
| アナリスト検証による修正 | 1.0 → 2.0 | 検証フィードバック反映 |
