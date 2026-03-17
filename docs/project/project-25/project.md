# finance-news-workflow コンテキスト最適化

**作成日**: 2026-01-29
**ステータス**: 計画中
**GitHub Project**: [#25](https://github.com/users/YH-05/projects/25) ✓

## 背景と目的

### 背景

- **種類**: 既存機能の改善（リファクタリング + 機能追加）
- **課題**: `/finance-news-workflow` コマンドでテーマ別サブエージェントがコンテキストオーバーを起こしている。各テーマエージェントが539-712行（6ファイル計4,002行）と巨大で、Issue作成からProject設定まで全て担当しているため処理中のコンテキストも肥大化する。加えて、ペイウォール記事の事前検出がなく本文取得不可の記事もIssue登録されてしまう。URL正規化も不十分で重複検出漏れが発生している。
- **期間**: 既存ワークフローの段階的改善

### 目的

1. テーマエージェントからIssue作成ロジックを分離し、コンテキスト使用量を60-70%削減する
2. ペイウォール記事を事前検出しスキップすることで、無駄なLLMコスト・不正確なIssue登録を防止する
3. URL正規化を強化し重複検出精度を向上させる
4. Issue本文を `.github/ISSUE_TEMPLATE/news-article.yml` に準拠させ品質を統一する

## スコープ

### 含むもの

- **変更範囲**: 新規作成 + 既存大幅修正
- **影響ディレクトリ**: `src/rss/`, `tests/rss/`, `.claude/agents/`, `.claude/skills/`, `.claude/rules/`

### 含まないもの

- オーケストレーターのURL抽出ロジック変更
- テーマ設定ファイル（`finance-news-themes.json`）の変更
- GitHub Project status別フィルタリング（GraphQL API未サポートのため不採用）
- 並列エージェント間の重複対策（RSS分担割り当てで対応済み）

## 成果物

| 種類 | 名前 | 説明 |
| ---- | ---- | ---- |
| Pythonモジュール | `article_content_checker.py` | ペイウォール/JS検出3段階チェック |
| テスト | `test_article_content_checker.py` | ユニットテスト |
| エージェント | `news-article-fetcher.md`（拡張） | ペイウォールチェック + Issue作成統合 |
| エージェント | テーマエージェント × 6（軽量化） | 各700行 → 200-300行 |
| エージェント | `finance-news-orchestrator.md`（修正） | セッションファイルにproject設定追加 |
| スキルガイド | `common-processing-guide.md`（更新） | 新フロー・バッチ処理・URL正規化 |
| ルール | `subagent-data-passing.md`（追記） | article-fetcher用データ構造 |

## 成功基準

- [ ] テーマエージェント行数が各200-300行に削減される（現状539-712行）
- [ ] ペイウォール記事がIssue登録前にスキップされる
- [ ] URL正規化強化（www.除去・フラグメント除去等）により重複検出精度が向上する
- [ ] Issue本文が `.github/ISSUE_TEMPLATE/news-article.yml` のフィールド構造に準拠する
- [ ] `/finance-news-workflow` がコンテキストオーバーなく完了する
- [ ] 既存の4セクション要約フォーマット・URL保持ルールが維持される

## 技術的考慮事項

### 改善後のアーキテクチャ

```
オーケストレーター (405行、変更なし)
├── 既存Issue取得（body → article_url 抽出、URL重複チェック維持）
└── セッションファイル作成（config に project_id 等追加）
    ↓
テーマエージェント × 6（各200-300行、並列実行）
├── RSS取得 → 日時フィルタ → テーママッチ → 重複チェック（URL正規化強化済み）
└── 5件ずつ news-article-fetcher に委譲（バッチ処理）
    ↓
news-article-fetcher（拡張版、Sonnet）
├── ペイウォール/JS事前チェック（Python: article_content_checker.py）
├── チェック通過 → WebFetch → 要約生成
├── チェック不通過 → スキップ（stats記録）
├── Issue作成（gh issue create + close）※ news-article.yml 準拠
├── Project追加（gh project item-add）
├── Status設定（GraphQL API）
└── 公開日時設定（GraphQL API）
```

### ペイウォール検出 3段階チェック

| Tier | 方法 | 速度 | 発動条件 |
|------|------|------|----------|
| 1 | httpx + lxml | ~0.5s | 常時 |
| 2 | Playwright (headless Chromium) | ~3-5s | Tier 1で本文不十分時 |
| 3 | ペイウォール指標チェック | 即時 | Tier 1/2通過後 |

### 依存パッケージ追加

- `playwright>=1.49.0`（Tier 2用、headless Chromium）

### リスクと対策

| リスク | 対策 |
|--------|------|
| article-fetcherの責務増大でSonnetコスト増 | バッチ5件で呼び出し回数を制限。ペイウォール事前スキップでWebFetch削減 |
| article-fetcher内でgh/GraphQL失敗 | 個別記事の失敗は次の記事に影響しない設計 |
| テーマエージェント軽量化で情報不足 | テーマ固有情報（キーワード・判定基準・判定例）は全て残す |
| ペイウォール誤検出（false positive） | 閾値を保守的に設定。checker失敗時はWebFetchにフォールスルー |
| URL正規化強化による既存データとの不整合 | 正規化は比較時のみ適用。保存URLは変更しない |

## タスク一覧

### Phase 0: ペイウォール/JS検出スクリプト

- [ ] article_content_checker.py 新規作成（3段階チェック + CLI）
  - Issue: [#1783](https://github.com/YH-05/quants/issues/1783)
  - ステータス: todo
  - 対象: `src/rss/services/article_content_checker.py`, `tests/rss/unit/test_article_content_checker.py`, `pyproject.toml`

### Phase 4.1: オーケストレーター設定追加

- [ ] セッションファイルにproject_id等3フィールド追加
  - Issue: [#1784](https://github.com/YH-05/quants/issues/1784)
  - ステータス: todo
  - 対象: `.claude/agents/finance-news-orchestrator.md`

### Phase 1: article-fetcher拡張

- [ ] news-article-fetcher 拡張（ペイウォールチェック + Issue作成統合）
  - Issue: [#1785](https://github.com/YH-05/quants/issues/1785)
  - ステータス: todo
  - 対象: `.claude/agents/news-article-fetcher.md`
  - 依存: #1783

### Phase 3: 共通処理ガイド更新・URL正規化強化

- [ ] 共通処理ガイドの新フロー反映・バッチ処理・URL正規化
  - Issue: [#1786](https://github.com/YH-05/quants/issues/1786)
  - ステータス: todo
  - 対象: `.claude/skills/finance-news-workflow/common-processing-guide.md`
  - 依存: #1785

### Phase 2: テーマエージェント軽量化

- [ ] テーマエージェント6ファイルの軽量化（各700行→200-300行）
  - Issue: [#1787](https://github.com/YH-05/quants/issues/1787)
  - ステータス: todo
  - 対象: `.claude/agents/finance-news-{index,stock,sector,macro,ai,finance}.md`
  - 依存: #1785, #1786

### Phase 4.2: ルール更新

- [ ] subagent-data-passing.md に article-fetcher 用データ構造追記
  - Issue: [#1788](https://github.com/YH-05/quants/issues/1788)
  - ステータス: todo
  - 対象: `.claude/rules/subagent-data-passing.md`
  - 依存: #1785

### 統合テスト

- [ ] 全フェーズの統合動作確認
  - Issue: [#1789](https://github.com/YH-05/quants/issues/1789)
  - ステータス: todo
  - 依存: #1783, #1784, #1785, #1786, #1787, #1788

## 実装順序

```
[並列] #1783 (Phase 0) + #1784 (Phase 4.1)
   ↓
#1785 (Phase 1: article-fetcher拡張)
   ↓
[並列] #1786 (Phase 3) + #1788 (Phase 4.2)
   ↓
#1787 (Phase 2: テーマエージェント軽量化)
   ↓
#1789 (統合テスト)
```

## 期待効果

| 指標 | 現状 | 改善後 |
|------|------|--------|
| テーマエージェント行数 | 539-712行 | 200-300行（57-68%削減） |
| テーマエージェント内のIssue作成コード | 約250行 | 0行（article-fetcherに移管） |
| 1バッチの処理件数 | 全記事（最大50件） | 5件 |
| ペイウォール記事のIssue登録 | 検出なし（そのまま登録） | 事前スキップ（3段階チェック） |
| URL重複チェック精度 | 基本的な正規化のみ | www.除去・フラグメント除去・追加パラメータ対応 |
| Issue本文の品質 | テンプレートと不整合 | news-article.yml 準拠 |

## 変更ファイル一覧

| ファイル | 変更種別 | Phase |
|---------|---------|-------|
| `src/rss/services/article_content_checker.py` | **新規作成** | 0 |
| `tests/rss/unit/test_article_content_checker.py` | **新規作成** | 0 |
| `pyproject.toml` | 依存追加 | 0 |
| `.claude/agents/news-article-fetcher.md` | 大幅修正 | 1 |
| `.claude/agents/finance-news-orchestrator.md` | 軽微修正 | 4.1 |
| `.claude/agents/finance-news-index.md` | 大幅修正 | 2 |
| `.claude/agents/finance-news-stock.md` | 大幅修正 | 2 |
| `.claude/agents/finance-news-sector.md` | 大幅修正 | 2 |
| `.claude/agents/finance-news-macro.md` | 大幅修正 | 2 |
| `.claude/agents/finance-news-ai.md` | 大幅修正 | 2 |
| `.claude/agents/finance-news-finance.md` | 大幅修正 | 2 |
| `.claude/skills/finance-news-workflow/common-processing-guide.md` | 修正 | 3 |
| `.claude/rules/subagent-data-passing.md` | 追記 | 4.2 |

## 参照

- 実装プラン: `docs/plan/2026-01-28-finance-news-context-optimization.md`

---

**進捗**: 0/7 完了 (0%)
**最終更新**: 2026-01-29
