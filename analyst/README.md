# analyst/ - アナリスト Y の投資哲学 AI 再現プロジェクト

## プロジェクト概要

外国株式アクティブファンドの運用チームにおいて、ファンドマネージャー Y の投資判断ロジック・暗黙知を AI エージェントに落とし込み、以下を実現する。

| 目標 | 説明 |
|------|------|
| 競争優位性評価の AI 再現 | Y の判断軸で競争優位性を自動スコアリング（10/30/50/70/90%） |
| 評価パイプラインの構築 | アナリストレポート → 確信度スコア + コメント |
| 大規模投資戦略への拡張 | トランスクリプト → 30 銘柄ポートフォリオ（CA Strategy PoC） |
| 継続的改善ループ | Y のフィードバック → ルール精緻化 → 再評価 |

---

## 現在位置

```
Phase 0  ████████████████████  ✅ 完了
Phase 1  █████████████░░░░░░░  ⏳ 進行中（6銘柄完成、Dogma 統合待ち）
Phase 2  ████████░░░░░░░░░░░░  ⏳ 進行中（Y の直接評価 5銘柄完成）
CA Strategy PoC  ████████████████░░░░  ⏳ 進行中（パッケージ実装完了、検証中）
```

---

## フェーズ構成

### Phase 0: 投資哲学の注入 ✅ 完了

Y の判断軸（Dogma）を明文化し、AI に注入できる形に整理する。

**成果物**:
- `Competitive_Advantage/analyst_YK/dogma.md` — Y の判断軸（AI 参照用、運用版）
- `Competitive_Advantage/analyst_YK/dogma_draft.md` — Y の判断軸（Y 検証用、○/×/△ チェックリスト）
- `Competitive_Advantage/analyst_YK/kb1_rules/` — KB1: 8ルール（却下基準）
- `Competitive_Advantage/analyst_YK/kb2_patterns/` — KB2: 12パターン（却下 A-G + 高評価 I-V）
- `Competitive_Advantage/analyst_YK/kb3_fewshot/` — KB3: 5企業 few-shot 例（CHD, COST, LLY, MNST, ORLY）
- `memo/phase0_discussion_log.md` — 設計議論 9 項目全解決
- `memo/discussion_summary.md` — 設計サマリー（22 判断確定）

**Y の判断軸（スコア体系）**:

| 確信度 | 意味 | 特徴 |
|--------|------|------|
| 90% | かなり納得 | 構造的優位性 + 明確な CAGR 接続 + 定量的裏付け |
| 70% | おおむね納得 | 妥当な仮説 + 一定の裏付け |
| 50% | まあ納得 | 方向性は認めるが裏付け不足（最頻値: 35%） |
| 30% | あまり納得しない | 飛躍的解釈・因果関係の逆転 |
| 10% | 却下 | 事実誤認・競争優位性として不成立 |

**設計確定事項（Phase 0 議論 22 項目）**:

| カテゴリ | 決定内容 |
|----------|---------|
| ルール体系 | 12ルール + 2補足（ブランド4類型 + CAGR確度統合）で確定 |
| アーキテクチャ | ハイブリッド（ゲートキーパー常時注入 + 残り RAG） |
| ワークフロー | 4ステップ（主張/ファクト分離 → 構造化出力 → ファクトチェック → 検証） |
| PoC 対象 | 新規銘柄（アウトオブサンプル）、他アナリスト執筆済みレポートから選定 |
| 品質測定 | 方式 C（テキストフィードバック定性評価） |
| CAGR パラメータ統合 | ルール 5 補足として注入 |

---

### Phase 1: 仮説生成 ⏳ 進行中

アナリストレポートから競争優位性仮説を構造化・抽出する。

**完成**: AI 生成レポート 6 銘柄

| ファイル | 銘柄 | ステータス |
|---------|------|-----------|
| `phase1/ANET_phase1.md` | ANET | ✅ |
| `phase1/pattern1_CHD_phase1.md` | CHD | ✅ |
| `phase1/pattern1_LLY_phase1.md` | LLY | ✅ |
| `phase1/pattern1_MNST改_phase1.md` | MNST | ✅ |
| `phase1/pattern1_ORLY_phase1.md` | ORLY | ✅ |
| `phase1/pattern_1_CDNS改_phase1.md` | CDNS | ✅ |

**残課題**:
- [ ] Phase 1 生成プロンプト（`template_ver2.md`）を Dogma と整合させる
- [ ] 「結果 vs 原因」「戦略 vs 優位性」を生成段階で強制する
- [ ] 期初レポート（①）と四半期レビュー（②）の重み付けを明示化する

---

### Phase 2: 評価 ⏳ 進行中

Phase 1 仮説を Y の判断軸で評価し、確信度スコア + コメントを生成する。

**完成**: Y による直接評価 5 銘柄（計 70 項目）

| ファイル | 銘柄 | 優位性評価 | CAGR評価 | ステータス |
|---------|------|-----------|---------|-----------|
| `phase2_KY/pattern1_CHD_phase2.md` | CHD | 6項目 | 対応あり | ✅ |
| `phase2_KY/pattern1_COST_phase2.md` | COST | 5項目 | 対応あり | ✅ |
| `phase2_KY/pattern1_LLY_phase2.md` | LLY | 5項目 | 対応あり | ✅ |
| `phase2_KY/pattern1_MNST_phase2.md` | MNST | 6項目 | 対応あり | ✅ |
| `phase2_KY/phase1_ORLY_phase2.md` | ORLY | 5項目 | 対応あり | ✅ |

**銘柄別平均スコア（Y の実評価）**:

| 銘柄 | 平均確信度 | 特記事項 |
|------|-----------|---------|
| ORLY | 63% | 市場構造との合致が最高評価 |
| CHD | 50% | 能力 vs 結果の区別が明確 |
| LLY | 47% | 業界共通能力を厳しく批判 |
| MNST | 40% | シェア=結果の原則を厳格適用 |
| COST | 39% | 最も分散が大きい |

**残課題**:
- [ ] Y による `dogma_draft.md` の ○/×/△ 検証（人間アクション）
- [ ] In-sample 検証: CHD/MNST で AI スコア vs Y 実スコアの乖離分析
- [ ] Out-of-sample 検証: 学習データ外の銘柄で評価実行

---

### CA Strategy PoC（Phase 2 並行）⏳ 進行中

トランスクリプトベースの投資戦略パイプライン（~300 銘柄 → 30 銘柄ポートフォリオ）。

**場所**: `src/dev/ca_strategy/`

**5 フェーズパイプライン**:

| フェーズ | 処理 | ステータス |
|---------|------|-----------|
| Phase 0 | トランスクリプト前処理（S&P Capital IQ JSON → 銘柄別 JSON） | ✅ |
| Phase 1 | 主張抽出（Claude Sonnet 4、5-15 件/銘柄） | ✅ |
| Phase 2 | スコアリング（KB1-T/KB2-T/KB3-T 参照、確信度 10-90%） | ✅ |
| Phase 3a | スコア集約（構造的重み付き） | ✅ |
| Phase 3b | セクター中立化（Z-score ランキング） | ✅ |
| Phase 4 | ポートフォリオ構築（30 銘柄選定） | ✅ |
| Phase 5 | 出力生成（JSON/CSV/Markdown + 銘柄別 rationale） | ✅ |

**PoC 対象**: MSCI Kokusai ベンチマーク（~300 銘柄）、2015-09-30 時点（ルックアヘッドバイアス防止）

**推定コスト**: ~$30 全フェーズ（Claude Sonnet 4、600 API 呼び出し）

---

### CA Eval ワークフロー実行 ✅ 12 銘柄完了

`/ca-eval` コマンドによる競争優位性評価の実行結果。

| 銘柄 | 実行フォルダ | ステータス |
|------|------------|-----------|
| AME | `research/CA_eval_20260220-0845_AME/` | ✅ |
| ATCOA | `research/CA_eval_20260220-0845_ATCOA/` | ✅ |
| CPRT | `research/CA_eval_20260220-0932_CPRT/` | ✅ |
| LLY | `research/CA_eval_20260220-1411_LLY/` | ✅ |
| MCO | `research/CA_eval_20260220-0931_MCO/` | ✅ |
| MSFT | `research/CA_eval_20260220-1411_MSFT/` | ✅ |
| MNST | — | ✅ |
| NFLX | `research/CA_eval_20260220-0931_NFLX/` | ✅ |
| ORLY | — | ✅ |
| POOL | `research/CA_eval_20260220-1411_POOL/` | ✅ |
| VRSK | `research/CA_eval_20260220-1411_VRSK/` | ✅ |

各実行フォルダ構成:
```
CA_eval_{datetime}_{TICKER}/
├── 00_meta/          research-meta.json
├── 01_data_collection/  parsed-report.json, sec-data.json
├── 02_claims/        claims.json
├── 03_verification/  fact-check.json, pattern-verification.json
└── 04_output/        structured.json, critique.json, draft-report.md, revised-report.md
```

---

## 次のマイルストーン

### 最優先（ボトルネック）

1. **Y による `dogma_draft.md` の ○/×/△ 検証** — 人間アクション待ち
   - `Competitive_Advantage/analyst_YK/dogma_draft.md` の Q1-Q6 に回答
   - 完了後に In-sample 検証へ進行可能

### 短期（1-2 週間）

2. **In-sample 検証の実行**
   - CHD または MNST で AI スコアを生成
   - Y の実スコアとの乖離を分析
   - 却下パターン出現数・高評価パターン出現数をカウント

3. **Phase 1 プロンプト改善（Dogma 統合）**
   - `prompt/` 内のテンプレートを dogma.md と統合
   - 「結果 vs 原因」「戦略 vs 優位性」を生成段階で強制

### 中期（2-4 週間）

4. **Out-of-sample 検証**
   - Phase 2 学習データに含まれない銘柄で評価実行（ANET, AME, CPRT 等）
   - Y にフィードバック依頼

5. **PoC 対象銘柄の決定・検証**
   - 他アナリスト執筆済みレポートから PoC 銘柄を選定
   - CA Strategy PoC の全フェーズ実行

---

## ディレクトリ構造

```
analyst/
├── plan/                   # 計画書・ロードマップ（決定事項・方針）
│   ├── 2026-02-06_session1-initial-plan.md
│   └── 2026-02-09_ai-investment-team-master.md
│
├── memo/                   # 議論ログ・思考過程・調査結果
│   ├── 2026-02-06_session1-discussion-log.md
│   ├── cagr_estimation_framework.md
│   ├── discussion_summary.md
│   ├── phase0_discussion_log.md
│   └── phase0_philosophy_injection_design.md
│
├── design/                 # 実装設計書・技術仕様
│   └── workflow_design.md
│
├── project/                # GitHub Project 連携用ドラフト・補足資料（現在未使用）
│
├── Competitive_Advantage/  # 競争優位性分析のナレッジベース（KB1/KB2/KB3）
│   ├── Competitive_Advantage_Dogma.md       # アナリスト K の判断軸（参考）
│   ├── Competitive_Advantage_template_ver2.md  # Phase 1 生成用テンプレート
│   └── analyst_YK/
│       ├── dogma.md                         # Y の判断軸（AI 参照用、運用版）
│       ├── dogma_draft.md                   # Y の判断軸（Y 検証用、○/×/△）
│       ├── feedback.md                      # Y のフィードバック記録
│       ├── judgment_patterns.md             # Phase 2 横断分析（12ルール）
│       ├── kb1_rules/                       # 8ルール（却下基準）
│       ├── kb2_patterns/                    # 12パターン（却下 A-G + 高評価 I-V）
│       └── kb3_fewshot/                     # 5企業 few-shot 例
│
├── transcript_eval/        # トランスクリプト評価用ナレッジベース（KB1-T/KB2-T/KB3-T）
│   ├── kb1_rules_transcript/                # 9ルール（rule12: 一次/二次情報判定を追加）
│   ├── kb2_patterns_transcript/             # 12パターン（同一）
│   ├── kb3_fewshot_transcript/              # 5企業 few-shot 例（同一）
│   ├── seven_powers_framework.md            # 7 Powers フレームワーク参照
│   └── system_prompt_transcript.md          # トランスクリプト評価用システムプロンプト
│
├── raw/                    # アナリストレポート生データ（12銘柄）
│   └── AME, ATCOA, CPRT, LLY, LRCS, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK
│
├── phase1/                 # Phase 1 AI 生成レポート（6銘柄）
│   └── ANET, CHD, LLY, MNST, ORLY, CDNS
│
├── phase2_KY/              # Phase 2 Y による評価（5銘柄）
│   └── CHD, COST, LLY, MNST, ORLY
│
├── research/               # CA Eval 実行結果（12銘柄×複数回実行）
│   └── CA_eval_{datetime}_{TICKER}/（5フォルダ構成）
│
├── prompt/                 # プロンプトテンプレート
│   ├── seven_powers_extract.json
│   └── seven_powers_extract.md
│
└── archived/               # レガシーファイル（Dify 実装等）
```

---

## plan/ / memo/ / design/ の棲み分け

| ディレクトリ | 内容 | 判断基準 |
|-------------|------|---------|-|
| `plan/` | 決定事項・方針・ロードマップ | 「これを読めば何をやるかわかる」 |
| `memo/` | 議論記録・思考過程・調査結果 | 「なぜこの結論に至ったかの根拠」 |
| `design/` | 実装設計書・技術仕様 | 「どう実装するかの仕様」 |

---

## ナレッジベース構造

3 つの評価コンテキストで共通の KB（ナレッジベース）層を使用。

| KB | 内容 | アナリストレポート版 | トランスクリプト版 |
|----|------|---------------------|-------------------|
| **KB1** | 却下ルール | `Competitive_Advantage/analyst_YK/kb1_rules/`（8ルール） | `transcript_eval/kb1_rules_transcript/`（9ルール、rule12 追加） |
| **KB2** | 却下パターン(A-G) + 高評価パターン(I-V) | `Competitive_Advantage/analyst_YK/kb2_patterns/`（12パターン） | `transcript_eval/kb2_patterns_transcript/`（12パターン） |
| **KB3** | Few-shot 例（CHD, COST, LLY, MNST, ORLY） | `Competitive_Advantage/analyst_YK/kb3_fewshot/`（5企業） | `transcript_eval/kb3_fewshot_transcript/`（5企業） |

### トランスクリプト版の差分

- `rule12_transcript_primary_secondary.md` — トランスクリプト固有の一次情報/二次情報判定ルール
- `system_prompt_transcript.md` — トランスクリプト評価用システムプロンプト
- `seven_powers_framework.md` — 7 Powers フレームワーク参照

### Competitive_Advantage/ 関連ファイル

| ファイル | 説明 |
|---------|------|
| `Competitive_Advantage_Dogma.md` | 競争優位性判断の基本原則（アナリスト K） |
| `Competitive_Advantage_template_ver2.md` | 評価テンプレート v2 |
| `analyst_YK/dogma.md` | Y の投資哲学（AI 参照用、運用版） |
| `analyst_YK/dogma_draft.md` | dogma ドラフト版（Y 検証用、○/×/△） |
| `analyst_YK/feedback.md` | フィードバック記録 |
| `analyst_YK/judgment_patterns.md` | Phase 2 横断分析（12ルール、5銘柄 70 項目から抽出） |

---

## 分析フェーズ

| フェーズ | ディレクトリ | 対象銘柄 | ステータス |
|---------|-------------|---------|-----------|
| Raw データ | `raw/` | AME, ATCOA, CPRT, LLY, LRCS, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK（12銘柄） | ✅ |
| Phase 1 | `phase1/` | ANET, CHD, LLY, MNST, ORLY, CDNS（6銘柄） | ✅（Dogma 統合待ち） |
| Phase 2 (KY) | `phase2_KY/` | CHD, COST, LLY, MNST, ORLY（5銘柄） | ✅（In-sample 検証待ち） |
| CA Eval | `research/` | AME, ATCOA, CPRT, LLY, MCO, MNST, MSFT, NFLX, ORLY, POOL, VRSK（11銘柄） | ✅ |

---

## 命名規約

- `plan/`, `memo/` 内の新規ファイル: `YYYY-MM-DD_descriptive-name.md`
- `memo/` 既存ファイルはそのまま維持

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

## 関連コマンド

| コマンド | 説明 |
|----------|------|
| `/ca-eval` | 競争優位性評価ワークフロー（KB1/KB2/KB3 + SEC EDGAR + 業界データ） |
| `/dr-stock` | 個別銘柄の包括的分析 |
| `/dr-industry` | 業界・セクター分析 |
| `/finance-research` | 金融リサーチ |

---

## 関連パッケージ

| パッケージ | 説明 |
|-----------|------|
| `dev/ca_strategy` | AI 駆動の競争優位性ベース投資戦略（PoC）— transcript_eval/ の KB を使用 |
