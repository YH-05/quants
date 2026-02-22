# analyst/ ディレクトリ再構成プラン

## Context

`analyst/` と `docs/AI_Invest_Team/` に分散している「アナリスト Y の投資哲学 AI 再現プロジェクト」の関連ファイルを `analyst/` に統合する。同時に `analyst/` 内に `plan/` と `project/` を新設し、ドメイン固有のドキュメント管理体系を確立する（`docs/plan/` や `docs/project/` とは区別）。

---

## 再構成後のディレクトリ構造

```
analyst/
├── README.md                        # [新設] 構造説明・運用ルール
│
├── plan/                            # [新設] 計画書・ロードマップ
│   ├── 2026-02-06_session1-initial-plan.md     # ← docs/AI_Invest_Team/plan.md
│   └── 2026-02-09_ai-investment-team-master.md # ← ai_investment_team.md
│
├── memo/                            # [既存] 議論ログ・思考過程（既存6ファイル + 1追加）
│   ├── 2026-02-06_session1-discussion-log.md   # ← docs/AI_Invest_Team/discussion_session1.md
│   └── (既存6ファイルは変更なし)
│
├── project/                         # [新設] GitHub Project 連携用（初期は空）
│
├── design/                          # [リネーム] claude_code/ → design/
│   ├── dify_comparison.md
│   └── workflow_design.md
│
├── Competitive_Advantage/           # 変更なし
├── transcript_eval/                 # 変更なし
├── dify/                            # 変更なし
├── raw/                             # 変更なし
├── phase1/                          # 変更なし
├── phase2_KY/                       # 変更なし
└── prompt/                          # 変更なし
```

**削除対象:**
- `analyst/dify_workflow_design.md` — 非推奨（`memo/dify_workflow_design.md` に移行済み）
- `docs/AI_Invest_Team/` — 全ファイル移動後にディレクトリ削除

---

## plan/ / memo/ / design/ の棲み分け

| ディレクトリ | 内容 | 判断基準 |
|-------------|------|---------|
| `plan/` | 決定事項・方針・ロードマップ | 「これを読めば何をやるかわかる」 |
| `memo/` | 議論記録・思考過程・調査結果 | 「なぜこの結論に至ったかの根拠」 |
| `design/` | 実装設計書・技術仕様 | 「どう実装するかの仕様」 |

命名規約: `YYYY-MM-DD_descriptive-name.md`（`memo/` 既存ファイルは変更なし）

---

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

---

## 操作手順

### Step 1: ディレクトリ作成

```bash
mkdir -p analyst/plan analyst/project
```

### Step 2: ファイル移動

```bash
# docs/AI_Invest_Team/ → analyst/ 統合
git mv docs/AI_Invest_Team/plan.md analyst/plan/2026-02-06_session1-initial-plan.md
git mv docs/AI_Invest_Team/discussion_session1.md analyst/memo/2026-02-06_session1-discussion-log.md

# マスタープランを plan/ に移動
git mv analyst/ai_investment_team.md analyst/plan/2026-02-09_ai-investment-team-master.md

# claude_code/ → design/ リネーム
git mv analyst/claude_code analyst/design
```

### Step 3: 不要ファイル削除

```bash
rm analyst/dify_workflow_design.md
rm -r docs/AI_Invest_Team/
```

### Step 4: 参照パス更新（6ファイル）

`analyst/claude_code/` → `analyst/design/` の変更:

| ファイル | 変更箇所 |
|---------|---------|
| `.claude/agents/deep-research/ca-eval-lead.md` | `analyst/claude_code/` → `analyst/design/` |
| `.claude/skills/ca-eval/SKILL.md` | 同上 |
| `docs/project/project-49/original-plan.md` | 同上 |
| `docs/project/project-49/project.md` | 同上 |
| `analyst/design/workflow_design.md` | 内部パス確認・更新 |
| `docs/plan/dify-workflow-claude-code-migration-plan.md` | 同上 |

`ai_investment_team.md` 移動の更新:

| ファイル | 変更箇所 |
|---------|---------|
| `docs/project/research-restructure/integrated-plan.md` | パスを `analyst/plan/2026-02-09_ai-investment-team-master.md` に更新 |

### Step 5: README.md 作成

`analyst/README.md` にディレクトリ構造・運用ルール・データフローを記載。

### Step 6: コミット

```
refactor(analyst): ディレクトリ再構成（AI_Invest_Team統合、plan/project/design新設）
```

---

## 検証

- [ ] `analyst/plan/` に 2 ファイル存在
- [ ] `analyst/memo/` に 7 ファイル存在（既存6 + 新規1）
- [ ] `analyst/design/` に 2 ファイル存在
- [ ] `docs/AI_Invest_Team/` が削除済み
- [ ] `analyst/dify_workflow_design.md` が削除済み
- [ ] `grep -r "analyst/claude_code" .` が 0 件
- [ ] `grep -r "docs/AI_Invest_Team" .` が 0 件（削除後の自己参照除く）
- [ ] 既存の ca-eval ワークフロー (`/ca-eval`) が正常動作
