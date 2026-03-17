# Issue #770 調査結果: 既存コード・テンプレートの調査

**調査日**: 2026-01-23
**Issue**: [#770](https://github.com/YH-05/quants/issues/770)
**関連プロジェクト**: [#21 週次市場動向レポート生成システム](https://github.com/users/YH-05/projects/21)

---

## 調査対象と結果

### 1. `/generate-market-report` コマンド

**ファイル**: `.claude/commands/generate-market-report.md`

**役割**: 週次マーケットレポート生成のメインコマンド

**主な機能**:
- 通常モード: データ収集→ニュース検索→レポート生成
- `--weekly-comment` モード: 火曜〜火曜の期間で3000字以上のコメント生成

**処理フロー**:
```
Phase 1: 初期化
├── 引数解析・出力ディレクトリ作成
├── 必要ツール確認（RSS MCP, Tavily, gh）
└── テンプレート確認

Phase 2: データ収集
├── Pythonスクリプト実行（weekly_comment_data.py）
└── returns.json, sectors.json, earnings.json 読み込み

Phase 3: ニュース検索
├── 指数関連ニュース検索
├── MAG7/半導体関連ニュース検索
├── セクター関連ニュース検索
└── 決算関連ニュース検索

Phase 4: レポート生成
├── テンプレート読み込み
├── データ埋め込み
├── ニュースコンテキスト追加
└── Markdownファイル出力

Phase 5: 完了処理
└── 結果サマリー表示
```

**GitHub Project #15 との連携**: 現状なし（リアルタイム検索のみ）

---

### 2. 週次コメント用サブエージェント

**ファイル**: `.claude/agents/weekly-comment-*-fetcher.md`

| エージェント | 役割 | 入力 | 出力 |
|-------------|------|------|------|
| `weekly-comment-indices-fetcher` | 指数関連ニュース収集 | `indices.json`, 期間 | 市場センチメント、上昇/下落要因、500字+コメント |
| `weekly-comment-mag7-fetcher` | MAG7関連ニュース収集 | `mag7.json`, 期間 | 銘柄別動向背景、800字+コメント |
| `weekly-comment-sectors-fetcher` | セクター関連ニュース収集 | `sectors.json`, 期間 | セクター別上昇/下落要因、上位/下位各400字+コメント |

**共通特徴**:
- モデル: haiku（軽量・高速）
- 検索順序: RSS MCP → Tavily → WebSearch
- 出力: JSON形式（commentary_draft含む）
- 並列実行対応

---

### 3. 市場データ収集スクリプト

**ファイル**: `scripts/weekly_comment_data.py`

**役割**: yfinance を使用した市場データ収集

**出力ファイル**:
| ファイル | 内容 |
|---------|------|
| `indices.json` | S&P500, RSP, VUG, VTV の週間リターン |
| `mag7.json` | MAG7 + SOX の週間リターン（ランク付き） |
| `sectors.json` | 全11セクターETF（上位3/下位3に分類） |
| `metadata.json` | 期間情報（日本語/英語フォーマット） |

**技術仕様**:
- データソース: yfinance (`yf.download`)
- 期間計算: 火曜〜火曜（`calculate_weekly_comment_period`）
- 日付ユーティリティ: `market_analysis.utils.date_utils`

---

### 4. テンプレートディレクトリ

**ファイル**: `template/market_report/`

**ディレクトリ構成**:
```
template/market_report/
├── 01_research/          # リサーチデータ格納
│   ├── analysis.json
│   ├── claims.json
│   ├── decisions.json
│   ├── fact-checks.json
│   ├── market_data/data.json
│   ├── queries.json
│   ├── raw-data.json
│   └── sources.json
├── 02_edit/              # 編集用
│   ├── critic.json
│   ├── critic.md
│   ├── first_draft.md
│   └── revised_draft.md
├── 03_published/
│   └── YYYYMMDD_article-title-en.md
├── article-meta.json
├── sample/
│   └── 20251210_weekly_comment.md  # サンプル（実例）
└── weekly_comment_template.md      # 週次コメントテンプレート
```

**weekly_comment_template.md のプレースホルダー**:
| プレースホルダー | 用途 | 最低文字数 |
|-----------------|------|-----------|
| `{indices_comment}` | 指数コメント | 500字 |
| `{mag7_comment}` | MAG7コメント | 800字 |
| `{top_sectors_comment}` | 上位セクターコメント | 400字 |
| `{bottom_sectors_comment}` | 下位セクターコメント | 400字 |
| `{upcoming_materials}` | 今後の材料 | 200字 |

---

### 5. GitHub Project #15 のデータ構造

**プロジェクト情報**:
- 名前: Finance News Collection
- Issue数: 445件（2026-01-23時点）

**フィールド一覧**:
| フィールド | タイプ | 選択肢/説明 |
|-----------|--------|------------|
| Title | Text | Issue タイトル |
| Status | SingleSelect | Index / Stock / Sector / Macro Economics / AI / Finance / Weekly Report |
| カテゴリ | SingleSelect | 米国株 / 日本株 / セクター分析 / テーマ投資 / マクロ経済 / その他 |
| 優先度 | SingleSelect | High / Medium / Low |
| 記事化状態 | SingleSelect | 未着手 / 執筆中 / 完了 |
| 収集日時 | Text | 収集日時 |
| 情報源 | Text | ニュースソース |
| 公開日時 | Text | 記事公開日時 |

**Issue本文構造**:
```markdown
## 日本語要約（400字程度）
[記事を読んで要約を追加してください]

## 記事概要
- **ソース**: Unknown
- **信頼性**: 0
- **公開日**: Unknown
- **URL**: No URL

## マッチしたキーワード
なし

## 次のアクション
- [ ] 記事を確認
- [ ] 日本語要約を追加（400字程度）
- [ ] 記事作成の必要性を判断
- [ ] 関連する既存記事があれば参照
```

---

## コンポーネント分析

### 再利用可能なコンポーネント

| コンポーネント | 再利用方法 | 備考 |
|--------------|-----------|------|
| `scripts/weekly_comment_data.py` | そのまま使用 | 市場データ収集の基盤 |
| `weekly-comment-*-fetcher` エージェント | 追加検索用として活用 | 不足分補完に有用 |
| `template/market_report/01_research/` | データ格納構造を参考 | JSON形式の統一 |
| `template/market_report/sample/20251210_weekly_comment.md` | 出力フォーマットの参考 | 実際の品質基準 |

### 新規作成が必要なコンポーネント

| コンポーネント | 説明 | 優先度 |
|--------------|------|-------|
| `weekly-report-news-aggregator` エージェント | GitHub Project #15 からニュースを集約 | High |
| `weekly-report-writer` エージェント | 統合データからレポートを生成 | High |
| `weekly_market_report_template.md` テンプレート | 新定型フォーマット（project.md の構成） | Medium |

### 修正が必要なコンポーネント

| コンポーネント | 修正内容 | 優先度 |
|--------------|---------|-------|
| `/generate-market-report` コマンド | GitHub Project 連携追加、`--weekly` オプション追加 | High |
| `generate-market-report` スキル | データフロー更新、新エージェント呼び出し追加 | High |

---

## 設計方針

### 1. 処理フローの拡張

```
/generate-market-report [--weekly]
    │
    ├── Phase 1: データ収集（既存）
    │   └── scripts/weekly_comment_data.py
    │       → indices.json, mag7.json, sectors.json, metadata.json
    │
    ├── Phase 2: GitHub Project ニュース取得（新規）
    │   └── weekly-report-news-aggregator エージェント
    │       ├── gh project item-list 15 --owner @me
    │       ├── Status フィールドでカテゴリ分類
    │       │   ├── Index → 指数関連
    │       │   ├── Stock → MAG7関連
    │       │   ├── Sector → セクター関連
    │       │   ├── Macro Economics → マクロ経済
    │       │   └── AI/Finance → 投資テーマ
    │       └── 期間フィルタリング（過去7日）
    │       → news_from_project.json
    │
    ├── Phase 3: 追加ニュース検索（既存活用）
    │   └── weekly-comment-*-fetcher（不足分補完）
    │       → news_supplemental.json
    │
    └── Phase 4: レポート生成（新規）
        └── weekly-report-writer エージェント
            ├── 新テンプレート適用
            ├── 市場データとニュースの統合
            └── セクション別コメント生成
            → weekly_report.md
```

### 2. データ分類ロジック

GitHub Project #15 の Status フィールドとレポートセクションのマッピング:

| Status | レポートセクション |
|--------|------------------|
| Index | 市場概況 > 主要指数パフォーマンス |
| Stock | Magnificent 7 + 半導体 |
| Sector | セクター分析 |
| Macro Economics | マクロ経済・政策動向 |
| AI | 投資テーマ別動向 |
| Finance | マクロ経済・政策動向 |
| Weekly Report | 今週のハイライト |

### 3. 出力ディレクトリ構造

```
articles/weekly_report_{YYYYMMDD}/
├── data/
│   ├── indices.json          # 既存スクリプト出力
│   ├── mag7.json             # 既存スクリプト出力
│   ├── sectors.json          # 既存スクリプト出力
│   ├── metadata.json         # 既存スクリプト出力
│   ├── news_from_project.json # 新規: GitHub Project からのニュース
│   └── news_supplemental.json # 新規: 追加検索結果
├── 02_edit/
│   └── weekly_report.md      # 新テンプレート適用
└── 03_published/
    └── (編集後の最終版)
```

---

## 次のステップ

1. **#771**: レポートテンプレートの設計
   - project.md の構成に基づく新テンプレート作成
   - 文字数要件の明確化

2. **#772**: GitHub Project ニュース取得エージェントの作成
   - `weekly-report-news-aggregator` エージェント
   - gh CLI を使用したニュース取得

3. **#773**: ニュースカテゴリ分類ロジックの実装
   - Status フィールドに基づく分類
   - 期間フィルタリング

---

**調査完了**: 2026-01-23
