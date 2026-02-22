# analyst/ - アナリスト Y の投資哲学 AI 再現プロジェクト

## ディレクトリ構造

```
analyst/
├── plan/                   # 計画書・ロードマップ（決定事項・方針）
├── memo/                   # 議論ログ・思考過程・調査結果
├── design/                 # 実装設計書・技術仕様
├── project/                # GitHub Project 連携用ドラフト・補足資料
├── Competitive_Advantage/  # 競争優位性分析のナレッジベース（KB1/KB2/KB3）
├── transcript_eval/        # トランスクリプト評価用ナレッジベース（KB1-T/KB2-T/KB3-T）
├── raw/                    # アナリストレポート生データ（12銘柄）
├── phase1/                 # Phase 1 分析成果物（6銘柄）
├── phase2_KY/              # Phase 2（KY分析）成果物（5銘柄）
├── prompt/                 # プロンプトテンプレート
└── archived/               # レガシーファイル（Dify実装等）
```

## plan/ / memo/ / design/ の棲み分け

| ディレクトリ | 内容 | 判断基準 |
|-------------|------|---------|
| `plan/` | 決定事項・方針・ロードマップ | 「これを読めば何をやるかわかる」 |
| `memo/` | 議論記録・思考過程・調査結果 | 「なぜこの結論に至ったかの根拠」 |
| `design/` | 実装設計書・技術仕様 | 「どう実装するかの仕様」 |

## ナレッジベース構造

3つの評価コンテキストで共通の KB（ナレッジベース）層を使用。

| KB | 内容 | アナリストレポート版 | トランスクリプト版 |
|----|------|---------------------|-------------------|
| **KB1** | 却下ルール | `Competitive_Advantage/analyst_YK/kb1_rules/`（8ルール） | `transcript_eval/kb1_rules_transcript/`（9ルール、rule12追加） |
| **KB2** | 却下パターン(A-G) + 高評価パターン(I-V) | `Competitive_Advantage/analyst_YK/kb2_patterns/`（12パターン） | `transcript_eval/kb2_patterns_transcript/`（12パターン） |
| **KB3** | Few-shot 例（CHD, COST, LLY, MNST, ORLY） | `Competitive_Advantage/analyst_YK/kb3_fewshot/`（5企業） | `transcript_eval/kb3_fewshot_transcript/`（5企業） |

### トランスクリプト版の差分

- `rule12_transcript_primary_secondary.md` — トランスクリプト固有の一次情報/二次情報判定ルール
- `system_prompt_transcript.md` — トランスクリプト評価用システムプロンプト
- `seven_powers_framework.md` — 7 Powers フレームワーク参照

### Competitive_Advantage/ 関連ファイル

| ファイル | 説明 |
|---------|------|
| `Competitive_Advantage_Dogma.md` | 競争優位性判断の基本原則 |
| `Competitive_Advantage_template_ver2.md` | 評価テンプレート v2 |
| `analyst_YK/dogma.md` | YK アナリストの投資哲学（dogma） |
| `analyst_YK/dogma_draft.md` | dogma ドラフト版 |
| `analyst_YK/feedback.md` | フィードバック記録 |
| `analyst_YK/judgment_patterns.md` | 判断パターン集 |

## 分析フェーズ

| フェーズ | ディレクトリ | 対象銘柄 |
|---------|-------------|---------|
| Phase 1 | `phase1/` | ANET, CHD, LLY, MNST, ORLY, CDNS（6銘柄） |
| Phase 2 (KY) | `phase2_KY/` | CHD, COST, LLY, MNST, ORLY（5銘柄） |
| Raw データ | `raw/` | AME, ATCOA, CPRT, LLY, LRCS, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK（12銘柄） |

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
| `/ca-eval` | 競争優位性評価ワークフロー（KB1/KB2/KB3 + SEC EDGAR + 業界データ） |
| `/dr-stock` | 個別銘柄の包括的分析 |
| `/dr-industry` | 業界・セクター分析 |
| `/finance-research` | 金融リサーチ |

## 関連パッケージ

| パッケージ | 説明 |
|-----------|------|
| `dev/ca_strategy` | AI 駆動の競争優位性ベース投資戦略（PoC）— transcript_eval/ の KB を使用 |
