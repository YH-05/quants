# 週次市場動向レポート生成システム

**作成日**: 2026-01-22
**ステータス**: 実装中
**GitHub Project**: [#21](https://github.com/users/YH-05/projects/21) ✓

## 背景と目的

### 背景

- **種類**: 新機能の追加
- **課題**: `/finance-news-workflow` で GitHub Project #15 に蓄積されたニュース（30件以上）が週次レポートに活用されていない。現在の `/generate-market-report --weekly-comment` はリアルタイム検索のみで、蓄積データを活用していない。
- **期間**: 新規機能として構築

### 目的

1. GitHub Project #15 に蓄積されたニュースを週次レポートの素材として活用する
2. 市場データ（指数、MAG7、セクター）とニュースを統合した包括的なレポートを生成する
3. note.com への投稿用コンテンツとして利用可能な品質を実現する
4. 将来的なグローバル市場対応への拡張性を確保する

## スコープ

### 含むもの

- **変更範囲**: 新規追加 + 既存修正（`/generate-market-report` コマンドの拡張）
- **影響ディレクトリ**: `.claude/`, `articles/`

### 含まないもの

- 自動定期実行（cron等）の設定。ただし将来実装する可能性あり。
- チャート・グラフの生成（テキストベースのみ）
- 日本市場・欧州市場の詳細分析（将来対応）

## 成果物

| 種類 | 名前 | 説明 |
| ---- | ---- | ---- |
| コマンド | `/generate-market-report` | 既存コマンドを拡張（GitHub Project 連携追加） |
| スキル | `generate-market-report` | レポート生成ロジックの詳細定義 |
| サブエージェント | `weekly-report-news-aggregator` | GitHub Project からニュースを集約 |
| サブエージェント | `weekly-report-writer` | 統合データからレポートを生成 |
| テンプレート | `weekly_market_report_template.md` | 定型フォーマットのテンプレート |
| Issueテンプレート | `weekly_report_issue_template.md` | GitHub Project #15 投稿用テンプレート |
| 出力 | `articles/weekly_report/{date}/` | 生成されたレポート（JSON + Markdown） |
| GitHub Issue | Project #15 Weekly Report | 週次レポートをIssueとして投稿 |

## 成功基準

- [x] `/generate-market-report` でレポートが正常に生成される
- [ ] GitHub Project #15 のニュースがレポートに統合される
- [ ] 週次レポートが GitHub Project #15 の「Weekly Report」カテゴリに Issue として投稿される
- [ ] 生成されたレポートが note 記事として最小限の編集で投稿可能
- [ ] 週次運用として継続的に使用できる安定性

## 技術的考慮事項

### 実装アプローチ

**シンプル優先**で実装し、以下の設計方針を採用：

1. **既存資産の活用**: `/generate-market-report --weekly-comment` を基盤として拡張
2. **GitHub Project 連携**: `gh project item-list` でニュースを取得
3. **2段階処理**:
   - Phase 1: データ収集（市場データ + GitHub Project ニュース）
   - Phase 2: レポート生成（テンプレートベース）

### データフロー

```
/finance-news-workflow
    │
    ▼
GitHub Project #15 (Finance News Collection)
    │ 蓄積されたニュース Issue
    ▼
/generate-market-report [--weekly]
    │
    ├── Phase 1: データ収集
    │   ├── 市場データ取得（yfinance/FRED）
    │   │   └── scripts/weekly_comment_data.py
    │   ├── GitHub Project ニュース取得
    │   │   └── gh project item-list 15 --owner @me
    │   └── 追加検索（RSS MCP / Tavily）
    │       └── 不足分を補完
    │
    ├── Phase 2: データ統合
    │   ├── ニュースをカテゴリ分類
    │   │   ├── 指数関連
    │   │   ├── MAG7関連
    │   │   ├── セクター関連
    │   │   └── マクロ経済関連
    │   └── 市場データとニュースを紐付け
    │
    ├── Phase 3: レポート生成
    │   ├── テンプレート読み込み
    │   ├── データ埋め込み
    │   └── Markdown/JSON 出力
    │
    └── Phase 4: GitHub Project 投稿
        ├── Issue テンプレートでレポートを整形
        ├── GitHub Issue 作成
        └── Project #15「Weekly Report」カテゴリに追加
```

### 出力ディレクトリ構造

```
articles/weekly_report/{YYYY-MM-DD}/
├── data/
│   ├── indices.json          # 指数パフォーマンス
│   ├── mag7.json             # MAG7 パフォーマンス
│   ├── sectors.json          # セクター分析
│   ├── news_from_project.json # GitHub Project からのニュース
│   ├── news_supplemental.json # 追加検索結果
│   └── metadata.json         # 期間・生成情報
├── 02_edit/
│   └── weekly_report.md      # Markdown レポート
└── 03_published/
    └── (公開用に編集後の最終版)
```

### GitHub Project #15 投稿

週次レポート生成後、GitHub Project #15 に Issue として投稿する。

**カテゴリフィールドの拡張**:
- 既存カテゴリ: 米国株, 日本株, セクター分析, テーマ投資, マクロ経済, その他
- 追加カテゴリ: **Weekly Report**（週次レポート用）

**Issue テンプレート形式**:
```markdown
## 週次マーケットレポート {YYYY-MM-DD}

**対象期間**: {start_date} 〜 {end_date}

### 今週のハイライト
{highlights}

### 主要指数
{indices_summary}

### 詳細レポート
📄 [Markdownレポート](articles/weekly_report/{date}/02_edit/weekly_report.md)

---
**生成日時**: {generated_at}
```

### レポート構成（定型フォーマット）

```markdown
# 週次マーケットレポート 2026/1/22
- 対象期間: 2026/1/15~2026/1/22

## 今週のハイライト
- サマリー（3-5 bullet points、トータル600字程度）

## 市場概況
### 主要指数パフォーマンス
| 指数 | 週間リターン | 要因分析 |
|------|-------------|---------|

### スタイル分析（グロース vs バリュー、大型vs中小型）
- スタイルETFなどから分析
- 大型/中古型の比較はS&P500時価総額ウェイト指数と等ウェイト指数との比較、Russell1000とRussell2000との比較から考察する。

## Magnificent 7 + 半導体
### パフォーマンス
| 銘柄 | 週間リターン | 注目ニュース |
|------|-------------|-------------|

### 個別銘柄トピック

#### (銘柄ティッカー: 銘柄名)
(トピックを600字程度で書く)

## セクター分析
### 上位3セクター

#### 上位1位セクター
(ニュースや背景を600字程度で書く)

#### 上位2位セクター
(ニュースや背景を600字程度で書く)

#### 上位3位セクター
(ニュースや背景を600字程度で書く)

#### 下位1位セクター
(ニュースや背景を600字程度で書く)

#### 下位2位セクター
(ニュースや背景を600字程度で書く)

#### 下位3位セクター
(ニュースや背景を600字程度で書く)

## マクロ経済・政策動向
- Fed 関連
- 経済指標

## 投資テーマ別動向
- AI/半導体
- その他注目テーマ

## 来週の注目材料
- 決算発表
- 経済指標発表

```

### 依存関係

- 既存: `/generate-market-report --weekly-comment`
- 既存: `scripts/weekly_comment_data.py`
- 既存: GitHub Project #15 (Finance News Collection)
- 既存: weekly-comment-*-fetcher エージェント群

### テスト要件

- **ユニットテスト**: ニュース分類ロジック
- **統合テスト**: GitHub Project 取得 → レポート生成の一連フロー

## タスク一覧

### Phase 1: 調査・設計 ✅

- [x] 既存コード・テンプレートの調査
  - Issue: [#770](https://github.com/YH-05/quants/issues/770)
  - ステータス: done
  - 見積もり: 1h

- [x] レポートテンプレートの設計
  - Issue: [#771](https://github.com/YH-05/quants/issues/771)
  - ステータス: done
  - 見積もり: 1h

### Phase 2: データ収集機能 ✅

- [x] GitHub Project ニュース取得エージェントの作成
  - Issue: [#772](https://github.com/YH-05/quants/issues/772)
  - ステータス: done
  - 見積もり: 2h

- [x] ニュースカテゴリ分類ロジックの実装
  - Issue: [#773](https://github.com/YH-05/quants/issues/773)
  - ステータス: done
  - 見積もり: 2h

### Phase 3: レポート生成機能

- [x] レポートテンプレートの作成
  - Issue: [#774](https://github.com/YH-05/quants/issues/774)
  - ステータス: done
  - 見積もり: 1h

- [ ] レポート生成エージェントの作成
  - Issue: [#775](https://github.com/YH-05/quants/issues/775)
  - ステータス: todo
  - 見積もり: 3h

### Phase 4: GitHub Project 連携 ✅

- [x] 週次レポート用 Issue テンプレートの作成
  - Issue: [#806](https://github.com/YH-05/quants/issues/806)
  - ステータス: done
  - 見積もり: 1h

- [x] GitHub Project #15 に「Weekly Report」カテゴリを追加
  - Issue: [#812](https://github.com/YH-05/quants/issues/812)
  - ステータス: done
  - 見積もり: 0.5h

- [x] レポート投稿エージェントの作成
  - Issue: [#813](https://github.com/YH-05/quants/issues/813)
  - ステータス: done
  - 見積もり: 2h

### Phase 5: 統合・コマンド更新

- [ ] /generate-market-report コマンドの拡張
  - Issue: [#776](https://github.com/YH-05/quants/issues/776)
  - ステータス: todo
  - 見積もり: 2h

- [ ] スキル定義の作成/更新
  - Issue: [#777](https://github.com/YH-05/quants/issues/777)
  - ステータス: todo
  - 見積もり: 1h

### Phase 6: テスト・検証

- [ ] 統合テストの実行
  - Issue: [#778](https://github.com/YH-05/quants/issues/778)
  - ステータス: todo
  - 見積もり: 1h

- [ ] サンプルレポート生成と品質確認
  - Issue: [#779](https://github.com/YH-05/quants/issues/779)
  - ステータス: todo
  - 見積もり: 1h

### Phase 7: ドキュメント

- [ ] CLAUDE.md の更新
  - Issue: [#780](https://github.com/YH-05/quants/issues/780)
  - ステータス: todo
  - 見積もり: 0.5h

---

---

**進捗**: 8/14 完了 (57%)
**最終更新**: 2026-01-23
