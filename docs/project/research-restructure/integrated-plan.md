# 3計画統合設計: リサーチシステム再構成

## Context

finance プロジェクトに3つの独立した計画が存在し、それぞれが deep-research エコシステムの異なる側面を拡張する。これらを統合的にロードマップ化し、**research-restructure を最優先**として段階的に実装する。

### 3計画の現状

| 計画 | 目的 | ステータス | 依存関係 |
|------|------|-----------|----------|
| **research-restructure** | deep-research を4コマンドに分割 + finance-research 特化 | 計画済み・未実装 | 他2計画の土台 |
| **ai-research-tracking** | AIバリューチェーン77社の自動収集 | 計画済み・未実装 | /dr-theme が必要 |
| **ai-investment-team** | 競争優位性評価の自動化 | Stage 2 進行中 | /dr-stock が必要 |

### なぜ research-restructure が最優先か

1. **他2計画の土台**: /dr-stock, /dr-theme が存在しないと統合ポイントが作れない
2. **既存 deep-research の問題**: dr-orchestrator はシンプルな逐次制御で Agent Teams 未使用。拡張性が低い
3. **明確な責務分離**: 分析（deep-research） vs コンテンツ作成（finance-research）を分けることで全体のアーキテクチャが整理される

---

## 統合アーキテクチャ

### 全体像

```
【レイヤー1: 常時データ収集】
/finance-news-workflow ──→ GitHub Project #15 (Finance News)
/ai-research-collect ───→ GitHub Project #XX (AI Value Chain)  ← ai-research-tracking
    ↓ 蓄積された Issue を参照

【レイヤー2: オンデマンド分析（deep-research 再構成）】
/dr-stock   → dr-stock-lead (Agent Teams)   → research/DR_stock_*/
/dr-industry→ dr-industry-lead (Agent Teams) → research/DR_industry_*/
/dr-macro   → dr-macro-lead (Agent Teams)   → research/DR_macro_*/
/dr-theme   → dr-theme-lead (Agent Teams)   → research/DR_theme_*/
    ↓ 分析結果ディレクトリ参照                    ↑ ai-research-tracking データ供給

【レイヤー3: 評価・レポート】
competitive-advantage-critique → Phase 2 評価   ← ai-investment-team
/finance-research --from-research {id} --format article|operations
    ↓
articles/{article_id}/（記事）or レポート出力
```

### データフロー図

```
入力ソース                       分析レイヤー                    出力
──────────                     ──────────                    ────
SEC EDGAR (src/edgar/) ──┐
yfinance (src/market/) ──┤
FRED (src/market/fred/)──┤     /dr-stock ──→ research/{id}/ ──→ /finance-research
Web検索 ─────────────────┤     /dr-industry    │                 --from-research
RSS (src/rss/) ──────────┤     /dr-macro       │                 → articles/
                         │     /dr-theme ←─────┘
                         │         ↑
GitHub Issues (蓄積) ────┘    ai-research-tracking
                                   ↑
analyst/raw/ ────────────→ competitive-advantage-critique
analyst/Competitive_Advantage/analyst_YK/dogma.md
```

### 共有コンポーネント

| コンポーネント | 利用元 | パス |
|---------------|--------|------|
| SEC EDGAR 取得 | /dr-stock, /dr-industry, /dr-theme, ai-invest | `src/edgar/`, MCP tools |
| 市場データ取得 | /dr-stock, /dr-industry, /dr-macro | `src/market/yfinance/`, `src/market/fred/` |
| 業界レポート収集 | /dr-stock, /dr-industry | `src/market/industry/`（新規） |
| Web検索 | 全 /dr-* | WebSearch, finance-web agent |
| RSS | /dr-*, ai-research-tracking | `src/rss/services/feed_reader.py` |
| クロス検証 | 全 /dr-* | dr-cross-validator（信頼度スコアリング統合）, dr-bias-detector |
| レポート生成 | 全 /dr-* | dr-report-generator |
| チャート出力 | 全 /dr-* | `src/analyze/visualization/`（Bash で Python 実行） |
| 評価エンジン | /dr-stock（オプション） | competitive-advantage-critique |

---

## 統合ロードマップ

### Phase 1: research-restructure（最優先）

#### Wave 1-1: 4スキル SKILL.md + テンプレート移行

**並列実行可能。** 既存テンプレートを各スキルディレクトリに移行。

| # | タスク | 入力 | 出力 |
|---|--------|------|------|
| 1-1-1 | dr-stock スキル作成 | `deep-research/research-templates/stock-analysis.md` | `.claude/skills/dr-stock/SKILL.md` |
| 1-1-2 | dr-industry スキル作成 | `sector-analysis.md` → `industry-analysis.md` リネーム | `.claude/skills/dr-industry/SKILL.md` |
| 1-1-3 | dr-macro スキル作成 | `macro-analysis.md` 移行 | `.claude/skills/dr-macro/SKILL.md` |
| 1-1-4 | dr-theme スキル作成 | `theme-analysis.md` 移行 | `.claude/skills/dr-theme/SKILL.md` |
| 1-1-5 | 出力テンプレート配置 | `deep-research/output-templates/` | 各スキルに `output-templates/` 配置 |

#### Wave 1-2: Lead エージェント（Agent Teams パターン）

**Wave 1-1 完了後。** research-lead.md を参考に4つの Lead を作成。

| # | タスク | 参考 | 出力 |
|---|--------|------|------|
| 1-2-1 | **dr-stock-lead** 作成 | research-lead.md のパターン | `.claude/agents/deep-research/dr-stock-lead.md` |
| 1-2-2 | dr-industry-lead 作成 | 1-2-1 を基準に | `.claude/agents/deep-research/dr-industry-lead.md` |
| 1-2-3 | dr-macro-lead 作成 | SEC省略 + economic-analysis 追加 | `.claude/agents/deep-research/dr-macro-lead.md` |
| 1-2-4 | dr-theme-lead 作成 | Web優先 + SEC(関連銘柄) | `.claude/agents/deep-research/dr-theme-lead.md` |

**各 Lead の共通ワークフロー（10タスク・5フェーズ）:**

深度モードなし。常にフルパイプライン実行。

```
Phase 0: TeamCreate → リサーチID生成 → ディレクトリ作成 → [HF0] 方針確認
Phase 1: データ収集（4並列: market-data, sec-filings, web, industry-researcher）
Phase 2: 統合+検証（2並列: source-aggregator, cross-validator[信頼度統合]）→ [HF1]
Phase 3: 分析（タイプ固有アナライザー）
Phase 4: 出力（report-generator + chart-renderer[Bash Python実行]）→ [HF2]
Phase 5: シャットダウン → TeamDelete
```

**廃止されたコンポーネント:**

| 廃止 | 理由 | 代替 |
|------|------|------|
| dr-confidence-scorer | cross-validator に統合 | dr-cross-validator |
| dr-visualizer エージェント | Python スクリプト実行に変更 | Bash + `src/analyze/visualization/` |
| depth モード（quick/standard/comprehensive） | 常にフル実行 | なし |
| Wikipedia データソース | 情報精度不足 | industry-researcher（コンサル/IB レポート） |

**タイプ別の差異:**

| Lead | Phase 1 | Phase 3 | データ優先度 |
|------|---------|---------|-------------|
| dr-stock-lead | 4タスク全て | dr-stock-analyzer | SEC > market > industry > Web |
| dr-industry-lead | 4タスク全て | dr-sector-analyzer | industry > market > SEC(top N) > Web |
| dr-macro-lead | SEC省略 + economic-analysis追加 | dr-macro-analyzer | FRED > Web > market |
| dr-theme-lead | industry変更 + theme固有ソース | dr-theme-analyzer | Web > industry > SEC(関連) > market |

**dr-stock-lead 詳細設計:** `docs/project/research-restructure/dr-stock-lead-design.md` 参照

#### Wave 1-3: コマンド（エントリポイント）

**Wave 1-2 完了後。** 各コマンドは対応する Lead にパラメータを渡すのみ。

| # | タスク | 出力 |
|---|--------|------|
| 1-3-1 | `/dr-stock` コマンド | `.claude/commands/dr-stock.md` |
| 1-3-2 | `/dr-industry` コマンド | `.claude/commands/dr-industry.md` |
| 1-3-3 | `/dr-macro` コマンド | `.claude/commands/dr-macro.md` |
| 1-3-4 | `/dr-theme` コマンド | `.claude/commands/dr-theme.md` |

#### Wave 1-4: finance-research 拡張 + 後方互換

**Wave 1-3 と並列実行可能。**

| # | タスク | 変更対象 |
|---|--------|---------|
| 1-4-1 | `--format`, `--from-research` オプション追加 | `.claude/commands/finance-research.md` |
| 1-4-2 | 参照モード + format 切り替え実装 | `.claude/agents/research-lead.md` |
| 1-4-3 | deep-research SKILL.md をルーター化 | `.claude/skills/deep-research/SKILL.md` |

#### Wave 1-5: ドキュメント更新

| # | タスク |
|---|--------|
| 1-5-1 | CLAUDE.md のコマンド・スキル・エージェント一覧更新 |
| 1-5-2 | Quants プロジェクトへの同期 |

#### Wave 1-0: 前提パッケージ（Wave 1-1 と並列可）

**dr-stock-lead の Phase 1 データ収集に必要な新規パッケージ・リファクタリング。**

| # | タスク | 出力 | 備考 |
|---|--------|------|------|
| 1-0-1 | `src/market/industry/` パッケージ作成 | コンサル/IB レポートスクレイピング + プリセット設定 | 別途 Issue |
| 1-0-2 | `MarketAnalysisProvider` 廃止・`MarketDataAnalyzer` 統合 | `src/analyze/integration/` に ticker info 追加 | 別途 Issue |

#### Wave 1 検証

```bash
# E2E テスト（深度モード廃止: 常にフル実行）
/dr-stock --ticker AAPL    → research/DR_stock_*_AAPL/ 生成確認
/dr-industry --sector technology → 動作確認
/dr-macro                   → FRED優先確認
/dr-theme --topic "AI半導体" → 動作確認
/finance-research --from-research DR_stock_*_AAPL --format article → 記事生成確認
/finance-research --article {id}             → 既存動作の回帰テスト
```

---

### Phase 2: ai-investment-team 統合（research-restructure 完了後）

research-restructure で `/dr-stock` が完成した後、competitive-advantage-critique を統合。

#### Wave 2-1: In-sample 検証（独立実行可能）

| # | タスク | 備考 |
|---|--------|------|
| 2-1-1 | CHD Phase 1 データで competitive-advantage-critique 実行 | AI vs Y スコア乖離測定 |
| 2-1-2 | MNST Phase 1 データで同上 | 目標: 平均±10%以内 |
| 2-1-3 | 乖離分析レポート作成 | Dogma改善ポイント特定 |

#### Wave 2-2: /dr-stock への統合

| # | タスク | 変更対象 |
|---|--------|---------|
| 2-2-1 | dr-stock-lead に `--enable-ca-critique` フラグ追加 | `dr-stock-lead.md` |
| 2-2-2 | Phase 3 分析後に competitive-advantage-critique を呼び出す分岐追加 | `dr-stock-lead.md` |
| 2-2-3 | stock-analysis.json から Phase 1 形式への変換ロジック | `dr-stock-analyzer.md` |

**接続設計:**
```
/dr-stock --ticker AAPL --enable-ca-critique
    Phase 3: dr-stock-analyzer → stock-analysis.json
        └── business_quality.competitive_advantages を抽出
        └── Phase 1 仮説形式に変換
    Phase 3.5 (新規): competitive-advantage-critique
        └── dogma.md 読込
        └── Phase 2 評価テーブル生成
        └── → 03_analysis/ca_evaluation.json
    Phase 4: レポートに評価結果を統合
```

#### Wave 2-3: CAGR推定フレームワーク統合（将来）

dr-stock-analyzer の分析にCAGR推定ロジックを組み込む。Phase 0（投資哲学注入）が設計急所。

| # | タスク |
|---|--------|
| 2-3-1 | Phase 0 投資哲学注入の実装（dogma.md + few-shot） |
| 2-3-2 | Phase 1 素材整理（10-K + アナリストレポート統合） |
| 2-3-3 | Phase 2 過去分解（売上CAGR分解） |
| 2-3-4 | Phase 3 前提条件構築（TAM × シェア × マージン） |

---

### Phase 3: ai-research-tracking 統合（/dr-theme 完了後）

/dr-theme が完成した後、AIバリューチェーン・トラッキングを構築・接続。

#### Wave 3-0: 共通基盤（TDD実装）

| # | タスク | 出力 |
|---|--------|------|
| 3-0-1 | データ型定義 | `src/rss/services/company_scrapers/types.py` |
| 3-0-2 | RobustScraper（UA+レートリミット+429+bot対策+フォールバック） | `src/rss/services/company_scrapers/robust_scraper.py` |
| 3-0-3 | テスト | `tests/rss/unit/services/company_scrapers/` |

#### Wave 3-1: Tier 3 アダプタ（5社）

| # | タスク | 出力 |
|---|--------|------|
| 3-1-1 | BaseCompanyScraper + Registry | `src/rss/services/company_scrapers/base.py` |
| 3-1-2 | 5社アダプタ（Perplexity, Cerebras, SambaNova, Lambda, Fanuc） | `adapters/*.py` |

#### Wave 3-2: セッションスクリプト + 企業定義

| # | タスク | 出力 |
|---|--------|------|
| 3-2-1 | 企業定義マスタ 77社 | `data/config/ai-research-companies.json` |
| 3-2-2 | セッションスクリプト | `scripts/prepare_ai_research_session.py` |
| 3-2-3 | ai-research-article-fetcher エージェント | `.claude/agents/ai-research-article-fetcher.md` |

#### Wave 3-3: /dr-theme との統合

| # | タスク | 変更対象 |
|---|--------|---------|
| 3-3-1 | dr-theme-lead に GitHub Issue 参照機能追加 | `dr-theme-lead.md` |
| 3-3-2 | dr-source-aggregator に Issue データソース追加 | `dr-source-aggregator.md` |

**接続設計:**
```
/dr-theme --topic "AI半導体"
    Phase 1: dr-source-aggregator
        └── 通常のデータ収集 + GitHub Issue 検索
            gh issue list --label ai-chips --label ai-semicon --json title,body,url
        └── 蓄積されたIssueをraw-data.jsonに統合
    Phase 3: dr-theme-analyzer
        └── バリューチェーン横断分析
            LLM → GPU → 製造装置 → DC → 電力 → 核融合
```

#### Wave 3-4: スキル + コマンド

| # | タスク | 出力 |
|---|--------|------|
| 3-4-1 | ai-research-workflow スキル | `.claude/skills/ai-research-workflow/` |
| 3-4-2 | `/ai-research-collect` コマンド | `.claude/commands/ai-research-collect.md` |
| 3-4-3 | GitHub Project 作成 | 手動作業 |

---

## 実装順序サマリー

```
Phase 1: research-restructure（最優先）
├── Wave 1-1: 4スキル作成 (並列)
├── Wave 1-2: 4 Lead エージェント (1-1完了後)
├── Wave 1-3: 4コマンド (1-2完了後)
├── Wave 1-4: finance-research 拡張 (1-3と並列)
└── Wave 1-5: ドキュメント更新

Phase 2: ai-investment-team 統合（/dr-stock 完了後）
├── Wave 2-1: In-sample 検証 (Phase 1 と並列可)
├── Wave 2-2: /dr-stock 統合
└── Wave 2-3: CAGR推定統合 (将来)

Phase 3: ai-research-tracking 統合（/dr-theme 完了後）
├── Wave 3-0: 共通基盤 TDD (Phase 1 と並列可)
├── Wave 3-1: Tier 3 アダプタ
├── Wave 3-2: セッションスクリプト
├── Wave 3-3: /dr-theme 統合
└── Wave 3-4: スキル + コマンド
```

### 並列実行可能なタスク

| タスク | 前提 | 備考 |
|--------|------|------|
| Wave 1-1 (4スキル) | なし | 4つ並列 |
| Wave 2-1 (In-sample検証) | なし | Phase 1 と独立 |
| Wave 3-0 (RobustScraper) | なし | Python TDD、Phase 1 と独立 |
| Wave 1-4 (finance-research) | Wave 1-3 | Wave 1-3 と並列も可 |

### クリティカルパス

```
Wave 1-0 ──→ Wave 1-2 ──→ Wave 1-3 ──→ Wave 1-5
(前提PKG)     (Lead)       (コマンド)    (ドキュメント)
    ↑             ↑
Wave 1-1 ────────┘
  (スキル)
```

Wave 1-0（industry パッケージ、market_analysis 廃止）と Wave 1-1（スキル作成）は並列実行可能。
両方完了後に Wave 1-2（Lead エージェント作成）に進む。

---

## 主要ファイル一覧

### 新規作成

| # | ファイル | Phase | 備考 |
|---|---------|-------|------|
| 1 | `.claude/skills/dr-stock/SKILL.md` | 1 | |
| 2 | `.claude/skills/dr-industry/SKILL.md` | 1 | |
| 3 | `.claude/skills/dr-macro/SKILL.md` | 1 | |
| 4 | `.claude/skills/dr-theme/SKILL.md` | 1 | |
| 5 | `.claude/agents/deep-research/dr-stock-lead.md` | 1 | 詳細設計書あり |
| 6 | `.claude/agents/deep-research/dr-industry-lead.md` | 1 | |
| 7 | `.claude/agents/deep-research/dr-macro-lead.md` | 1 | |
| 8 | `.claude/agents/deep-research/dr-theme-lead.md` | 1 | |
| 9 | `.claude/agents/deep-research/industry-researcher.md` | 1 | ★新設 |
| 10 | `.claude/commands/dr-stock.md` | 1 | |
| 11 | `.claude/commands/dr-industry.md` | 1 | |
| 12 | `.claude/commands/dr-macro.md` | 1 | |
| 13 | `.claude/commands/dr-theme.md` | 1 | |
| 14 | `src/market/industry/` パッケージ | 1-0 | スクレイピング基盤 |
| 15 | `data/config/industry-research-presets.json` | 1-0 | 業界分析プリセット |
| 16 | `src/rss/services/company_scrapers/robust_scraper.py` | 3 | |
| 17 | `src/rss/services/company_scrapers/base.py` | 3 | |
| 18 | `data/config/ai-research-companies.json` | 3 | |
| 19 | `scripts/prepare_ai_research_session.py` | 3 | |

### 変更

| # | ファイル | 変更内容 | Phase |
|---|---------|---------|-------|
| 1 | `.claude/commands/finance-research.md` | --format, --from-research 追加 | 1 |
| 2 | `.claude/agents/research-lead.md` | 参照モード + format切替 | 1 |
| 3 | `.claude/skills/deep-research/SKILL.md` | ルーター化 | 1 |
| 4 | `.claude/agents/deep-research/dr-cross-validator.md` | 信頼度スコアリング統合 | 1 |
| 5 | `.claude/agents/deep-research/dr-stock-analyzer.md` | depth モード削除 + CA評価統合 | 1, 2 |
| 6 | `.claude/agents/deep-research/dr-source-aggregator.md` | market_analysis 参照修正 + Issue参照追加 | 1, 3 |
| 7 | `src/analyze/integration/market_integration.py` | get_ticker_info() 追加 | 1-0 |
| 8 | `CLAUDE.md` | 全更新 | 各Phase末 |

### 廃止

| # | ファイル/コンポーネント | 理由 | 代替 |
|---|----------------------|------|------|
| 1 | dr-confidence-scorer エージェント | cross-validator に統合 | dr-cross-validator |
| 2 | dr-visualizer エージェント（独立実行） | Python スクリプト実行に変更 | Bash + analyze.visualization |
| 3 | `MarketAnalysisProvider` | MarketDataAnalyzer に統合 | analyze.integration |
| 4 | depth モード（quick/standard/comprehensive, shallow/deep/auto） | 常にフル実行 | なし |

### 参照（変更なし）

| ファイル | 用途 |
|---------|------|
| `.claude/agents/research-lead.md` | Lead パターンの参考 |
| `.claude/agents/competitive-advantage-critique.md` | Phase 2 統合 |
| `analyst/Competitive_Advantage/analyst_YK/dogma.md` | 評価基準 |
| `analyst/memo/cagr_estimation_framework.md` | CAGR統合設計 |
| `src/rss/services/article_extractor.py` | RobustScraper参考 |
| `scripts/prepare_news_session.py` | セッションスクリプト参考 |

---

## 検証方法

### Phase 1 完了時

```bash
# 各コマンドの動作確認
/dr-stock --ticker AAPL --depth quick
/dr-industry --sector technology --depth quick
/dr-macro --depth quick
/dr-theme --topic "AI半導体" --depth quick

# 出力ディレクトリ確認
ls research/DR_stock_*/
ls research/DR_industry_*/
ls research/DR_macro_*/
ls research/DR_theme_*/

# finance-research 連携
/finance-research --from-research DR_stock_YYYYMMDD_AAPL --format article
/finance-research --from-research DR_stock_YYYYMMDD_AAPL --format operations

# 後方互換
/finance-research --article {existing_id}  # 既存動作が壊れていないこと
```

### Phase 2 完了時

```bash
# In-sample 検証
# CHD の Phase 1 データで評価エージェント実行
# AI生成スコア vs Y実スコアの乖離 ≤ ±10%

# /dr-stock + CA評価
/dr-stock --ticker CHD --depth standard --enable-ca-critique
# → research/DR_stock_*/03_analysis/ca_evaluation.json 確認
```

### Phase 3 完了時

```bash
# データ収集
/ai-research-collect --days 7 --categories gpu_chips --top-n 5
# → GitHub Issue作成 + Project追加確認

# /dr-theme 統合
/dr-theme --topic "AI半導体" --depth standard
# → GitHub Issue データが raw-data.json に含まれること確認
```

---

## 旧プランとの関係

| 旧ファイル | 本プランでの扱い |
|-----------|----------------|
| `analyst/plan/2026-02-06_session1-initial-plan.md` | **旧 `docs/AI_Invest_Team/plan.md`**: analyst/ に統合 |
| `docs/project/research-restructure/project.md` | **Phase 1 の詳細版として維持** |
| `docs/project/ai-research-tracking/project.md` | **Phase 3 の詳細版として維持** |
| `analyst/plan/2026-02-09_ai-investment-team-master.md` | **旧 `analyst/ai_investment_team.md`**: Phase 2 の詳細版 |

本プランは3計画の**統合ロードマップ**であり、各計画の詳細な実装仕様は既存ドキュメントを参照する。
