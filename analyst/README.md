# analyst/ - アナリスト Y の投資哲学 AI 再現プロジェクト

## ディレクトリ構造

```
analyst/
├── plan/                   # 計画書・ロードマップ（決定事項・方針）
├── memo/                   # 議論ログ・思考過程・調査結果
├── design/                 # 実装設計書・技術仕様（旧 claude_code/）
├── project/                # GitHub Project 連携用ドラフト・補足資料
├── Competitive_Advantage/  # 競争優位性分析のナレッジベース
├── transcript_eval/        # トランスクリプト評価データ
├── dify/                   # Dify ワークフロー設計（レガシー参照用）
├── raw/                    # 生データ
├── phase1/                 # Phase 1 成果物
├── phase2_KY/              # Phase 2（KY分析）成果物
└── prompt/                 # プロンプトテンプレート
```

## plan/ / memo/ / design/ の棲み分け

| ディレクトリ | 内容 | 判断基準 |
|-------------|------|---------|
| `plan/` | 決定事項・方針・ロードマップ | 「これを読めば何をやるかわかる」 |
| `memo/` | 議論記録・思考過程・調査結果 | 「なぜこの結論に至ったかの根拠」 |
| `design/` | 実装設計書・技術仕様 | 「どう実装するかの仕様」 |

## 命名規約

- `plan/`, `memo/` 内の新規ファイル: `YYYY-MM-DD_descriptive-name.md`
- `memo/` 既存ファイルはそのまま維持

## project/ の運用ルール

```
analyst/plan/ で計画策定
    ↓
/plan-project で実装計画詳細化 → project.md 生成
    ↓
docs/project/project-{N}/ にエクスポート（GitHub Project 統合）
    ↓
analyst/project/ にはドラフトや analyst 固有の補足資料を保持
```

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/ca-eval` | 競争優位性評価ワークフロー |
| `/dr-stock` | 個別銘柄分析 |
| `/finance-research` | 金融リサーチ |
