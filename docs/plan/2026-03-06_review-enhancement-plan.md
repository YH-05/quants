# レビュー機能強化プラン

## Context

`issue-implement-single` で各Issue実装後のコードレビューが不十分。現状は `quality-checker`（format/lint/type/test）と `code-simplifier`（リファクタリング）のみで、設計・可読性・セキュリティ・テスト品質の観点が欠落している。また `issue-implementation-serial` で複数Issue実装時は `--skip-pr` により Phase 6.5（pr-design）もスキップされる。

最後に一括レビューするより、各Issue実装後にインクリメンタルに修正する方が低コストでロジックもシンプル。加えて、`review-pr` にクオンツ分析コードのレビュー機能（`quant-computing` スキル活用）を追加する。

---

## 変更概要

| 変更 | 対象 | 内容 |
|------|------|------|
| Phase 5.5 追加 | `issue-implement-single` | 3エージェント並列の簡易コードレビュー + 自動修正 |
| pr-quant 新規作成 | `review-pr` | クオンツ計算コード品質レビューエージェント（条件付き起動） |
| サマリー更新 | `issue-implementation-serial` | Phase 5.5 結果をサマリーに含める |
| インデックス更新 | `CLAUDE.md` | pr-quant 追加、エージェント数更新 |

---

## 1. issue-implement-single: Phase 5.5（簡易コードレビュー）追加

### 1.1 Phase 配置

Phase 5（quality-checker --auto-fix）の後、Phase 6（make check-all）の前に挿入。`--skip-pr` でも常に実行。

```
Phase 4:   コード整理（code-simplifier）
Phase 5:   品質保証（quality-checker --auto-fix）
Phase 5.5: 簡易コードレビュー（NEW、常に実行）  <-- ここ
Phase 6:   コミット前検証（make check-all）→ コミット
Phase 6.5: PR設計レビュー（pr-design、PR作成時のみ）
Phase 7:   CIチェック検証（PR作成時のみ）
```

### 1.2 使用エージェント（3並列）

| エージェント | チェック内容 | 選定理由 |
|---|---|---|
| `pr-readability` | 命名規則・型ヒント・Docstring | 軽量、規約違反の早期発見 |
| `pr-security-code` | OWASP A01-A05・機密情報検出 | セキュリティ脆弱性は早期発見が重要 |
| `pr-test-coverage` | テスト存在・カバレッジ・エッジケース | TDD原則によるテスト網羅性確認 |

除外: `pr-design`（Phase 6.5でPR単位で実施）、`pr-performance`（重い、緊急性低い）、`pr-test-quality`（pr-test-coverageと一部重複）

### 1.3 差分ベース入力

```bash
# 未コミットの変更（Phase 5.5 はコミット前に実行）
git diff HEAD               # 差分内容
git diff HEAD --name-only   # 変更ファイル一覧
# 初回Issue（コミットなし）の場合
git diff                    # ステージング前の全変更
```

### 1.4 プロンプト方針

各エージェントに対し **HIGH/CRITICAL のみ報告** を指示。MEDIUM/LOW は省略して軽量に保つ。

```
簡易レビューモード（Issue実装後の差分のみ対象）。
HIGH/CRITICAL の問題のみ報告してください。MEDIUM/LOW は省略。
```

### 1.5 自動修正フロー

```
Phase 5.5 結果集約
    |
    +-- HIGH/CRITICAL なし → Phase 6 へ
    |
    +-- HIGH/CRITICAL あり
        |
        +-- 修正実施（直接 Edit/Write）
        |   - 可読性: 命名修正、型ヒント追加、Docstring追加
        |   - セキュリティ: recommendation に基づき修正
        |   - テスト: 不足テストケース追加
        |
        +-- quality-checker --quick（修正後の整合性確認）
        |
        +-- 最大2サイクル。2回で修正不可 → 警告付きで Phase 6 へ続行
```

### 1.6 出力フォーマット

```yaml
incremental_review:
  status: passed | fixed | failed
  agents_run: 3
  issues_found: { critical: 0, high: 0 }
  issues_fixed: { critical: 0, high: 0 }
  issues_remaining: []  # status == failed の場合のみ
  fix_cycles: 0
```

### 1.7 修正ファイル

- `.claude/skills/issue-implement-single/SKILL.md`
  - Phase 5.5 の定義追加
  - フロー図更新
  - 完了条件に Phase 5.5 を追加
  - サマリー出力に incremental_review を追加

---

## 2. pr-quant エージェント新規作成

### 2.1 エージェント定義

ファイル: `.claude/agents/pr-quant.md`

```yaml
---
name: pr-quant
description: PRのクオンツ計算コード品質（数値精度・ベクトル化・バックテスト・リスク指標）を検証するサブエージェント
model: sonnet
color: purple
---
```

参照スキル: `@.claude/skills/quant-computing/SKILL.md`, `@.claude/skills/quant-computing/guide.md`

### 2.2 起動条件

変更ファイルが以下のパスに含まれる場合のみ起動:

```python
QUANT_PATHS = [
    "src/strategy/", "src/factor/", "src/analyze/",
    "src/market/", "src/dev/ca_strategy/",
    "tests/strategy/", "tests/factor/", "tests/analyze/",
    "tests/market/", "tests/ca_strategy/",
]
```

### 2.3 チェック項目（quant-computing MUST から抽出）

| ID | ルール | 重大度 |
|----|--------|--------|
| QC-01 | 浮動小数点の `==` 比較禁止（epsilon or pytest.approx） | HIGH |
| QC-02 | 単利年率化 `return * 252/n` 禁止（複利必須） | CRITICAL |
| QC-03 | バックテストの前方参照（signals.shift(1) 欠落、PoiT違反） | CRITICAL |
| QC-04 | pandas/NumPy 集計での Python ループ禁止 | MEDIUM |
| QC-05 | 数値計算関数の Hypothesis テスト不足 | MEDIUM |
| QC-06 | リスク指標のゼロ除算防御欠如（_EPSILON） | HIGH |
| QC-07 | スキーマ検証なしのデータ永続化 | HIGH |
| QC-08 | データ量/パターンに基づかない DB 選択 | LOW |

### 2.4 出力フォーマット

```yaml
pr_quant:
  score: 0  # 0-100
  numerical_precision: { float_equality_violations: 0, violations: [] }
  vectorization: { python_loop_violations: 0, violations: [] }
  return_calculation: { simple_annualization_violations: 0, violations: [] }
  backtesting: { lookahead_bias_violations: 0, point_in_time_violations: 0, violations: [] }
  risk_metrics: { zero_division_violations: 0, violations: [] }
  testing: { missing_hypothesis_tests: 0, violations: [] }
  data_pipeline: { unvalidated_persistence: 0, violations: [] }
  db_selection: { issues: [] }
  issues:
    - severity: "HIGH"
      category: "numerical_precision"
      rule_id: "QC-01"
      file: "[path]"
      line: 0
      description: "[description]"
      recommendation: "[fix]"
```

---

## 3. review-pr スキル更新

### 3.1 エージェント構成（7 → 7+1条件付き）

| グループ | エージェント | 条件 |
|---------|------------|------|
| コード品質 | pr-readability | 常時 |
| コード品質 | pr-design | 常時 |
| コード品質 | pr-performance | 常時 |
| コード品質 | **pr-quant** | **クオンツファイル変更時のみ** |
| セキュリティ | pr-security-code | 常時 |
| セキュリティ | pr-security-infra | 常時 |
| テスト | pr-test-coverage | 常時 |
| テスト | pr-test-quality | 常時 |

### 3.2 スコア出力方式

**変更前**: `code_quality` は加重平均の単一スコア（例: 82）

**変更後**: 加重平均を廃止し、各要素のスコアを直接出力する

```yaml
scores:
  code_quality:
    readability: 85      # pr-readability のスコア
    design: 90           # pr-design のスコア
    performance: 75      # pr-performance のスコア
    quant: 80            # pr-quant のスコア（null if not activated）

  security:
    code: 85             # pr-security-code のスコア
    infra: 90            # pr-security-infra のスコア

  test:
    coverage: 80         # pr-test-coverage のスコア
    quality: 75          # pr-test-quality のスコア
```

- 各エージェントのスコア（0-100）をそのまま出力
- 加重平均による情報損失をなくし、どの観点が弱いか一目でわかるようにする
- `quant` はクオンツファイル変更時のみ値が入る（それ以外は `null`）
- `security`, `test` も同様に要素別スコアに分解する（統一性のため）

### 3.3 Markdown 出力の更新

```markdown
## 総合評価

### コード品質
| 観点 | スコア | 評価 |
|------|--------|------|
| 可読性 | 85 | 良好 |
| 設計 | 90 | 良好 |
| パフォーマンス | 75 | 改善推奨 |
| クオンツ計算 | 80 | 良好 |

### セキュリティ
| 観点 | スコア | 評価 |
|------|--------|------|
| コードセキュリティ | 85 | 良好 |
| インフラセキュリティ | 90 | 良好 |

### テスト
| 観点 | スコア | 評価 |
|------|--------|------|
| カバレッジ | 80 | 良好 |
| テスト品質 | 75 | 改善推奨 |
```

評価基準: 80+ 良好 / 60-79 改善推奨 / 60未満 要対応

### 3.4 修正ファイル

- `.claude/skills/review-pr/SKILL.md`
  - pr-quant を8番目の条件付きエージェントとして追加
  - スコア出力を加重平均から要素別スコアに変更
  - YAML/Markdown 出力に quant セクション追加
  - エージェント一覧テーブル更新

---

## 4. issue-implementation-serial スキル更新

### 4.1 全体フロー（更新後）

現在の Step 6.5（pr-design 単独）を廃止し、**review-pr による包括的レビュー → 全指摘修正 → 再レビュー**のループに置き換える。

```
Step 1-5: 各Issue実装（issue-implement-single --skip-pr）
    各Issue内で Phase 5.5（簡易レビュー + 自動修正）実行済み
         |
Step 6: PR作成（git push + gh pr create）
         |
Step 7: PRレビュー＆修正ループ（NEW）
    |
    +---> 7.1: review-pr 実行（最大8エージェント並列）
    |         全レベルの指摘を収集（CRITICAL/HIGH/MEDIUM/LOW）
    |
    +---> 7.2: 指摘事項の修正
    |         全指摘（レベル問わず）を修正
    |         修正 → コミット → プッシュ
    |
    +---> 7.3: 再レビュー（7.1 に戻る）
    |         指摘が 0 件になるまで繰り返し
    |         最大3ラウンド（安全弁）
    |
    +---> 7.4: ラウンド上限到達時
              残存指摘を警告付きで報告し続行
         |
Step 8: CIチェック検証（gh pr checks --watch）
    |
    +-- 全パス → 完了
    +-- 失敗 → 修正 → 再検証（最大3回）
```

### 4.2 Step 7 詳細: PRレビュー＆修正ループ

#### 7.1 review-pr の実行

```yaml
# review-pr スキルを呼び出し（PRコメント投稿は最終ラウンドのみ）
Skill(review-pr)
```

- 最大8エージェント並列（pr-quant はクオンツファイル変更時のみ）
- **全レベルの指摘を収集**（HIGH/CRITICAL だけでなく MEDIUM/LOW も含む）
- 各エージェントの個別スコアを取得

#### 7.2 指摘事項の修正

レビュー結果から指摘事項を抽出し、全て修正する:

```
レビュー結果解析
    |
    +-- 指摘 0 件 → Step 8 へ（レビュー完了）
    |
    +-- 指摘あり → 全件修正
        |
        +-- コード品質（readability）: 命名修正、型ヒント追加、Docstring追加
        +-- 設計（design）: SOLID違反修正、重複削除、抽象化調整
        +-- パフォーマンス（performance）: アルゴリズム改善、N+1解消
        +-- クオンツ（quant）: epsilon比較追加、ベクトル化、shift(1)追加
        +-- セキュリティ（security）: 脆弱性修正、機密情報除去
        +-- テスト（test）: 不足テスト追加、テスト品質改善
        |
        +-- quality-checker --quick（修正後の整合性確認）
        +-- make check-all（コミット前検証）
        +-- git add & commit & push
        |
        +-- 7.1 に戻る（再レビュー）
```

#### 7.3 ラウンド制御

| ラウンド | 動作 |
|---------|------|
| 1 | 初回レビュー → 全指摘修正 |
| 2 | 再レビュー → 残存指摘修正 |
| 3 | 最終レビュー → 残存指摘修正 |
| 3超過 | 残存指摘を警告として報告、Step 8 へ続行 |

#### 7.4 PRコメント投稿タイミング

- ラウンド途中: PRコメント投稿しない（修正中のため）
- **最終ラウンド（指摘0件 or ラウンド上限）**: レビュー結果をPRコメントとして投稿

### 4.3 サマリー出力更新

```
## サマリー
- 実装したIssue: 3件
- 成功: 3件
- 作成したPR: #500
- インクリメンタルレビュー: 全Issue通過（Phase 5.5）
- PRレビュー: 全指摘修正済み（2ラウンド、修正12件）
- CIチェック: 全てパス

## Issue別結果
| Issue | タイトル | 状態 | コミット | 簡易レビュー |
|-------|----------|------|----------|-------------|
| #958 | ... | OK | abc1234 | passed |
| #959 | ... | OK | def5678 | fixed (2) |
| #960 | ... | OK | ghi9012 | passed |

## PRレビュー修正履歴
| ラウンド | 指摘数 | 修正数 | 残存 |
|---------|--------|--------|------|
| 1 | 10 | 10 | 0 |
| 2 | 2 | 2 | 0 |
| (最終) | 0 | - | 0 |
```

### 4.4 修正ファイル

- `.claude/skills/issue-implementation-serial/SKILL.md`
  - Step 6.5（pr-design単独）を廃止
  - Step 7 を「PRレビュー＆修正ループ」に置換（review-pr スキル使用）
  - Step 8 として CIチェック検証を移動
  - サマリー出力フォーマットに incremental_review と PRレビュー修正履歴を追加
  - 出力例の全面更新

---

## 5. CLAUDE.md 更新

- PRレビューエージェントテーブルに `pr-quant` 追加
- review-pr の説明を「7つのサブエージェント」→「最大8つのサブエージェント」に更新
- エージェント総数の更新

---

## 修正ファイル一覧

| ファイル | 操作 | 内容 |
|---------|------|------|
| `.claude/agents/pr-quant.md` | **新規作成** | クオンツ計算レビューエージェント定義 |
| `.claude/skills/issue-implement-single/SKILL.md` | 編集 | Phase 5.5 追加 |
| `.claude/skills/review-pr/SKILL.md` | 編集 | pr-quant 統合、スコア出力を要素別に変更 |
| `.claude/skills/issue-implementation-serial/SKILL.md` | 編集 | Step 6.5廃止、Step 7にレビュー修正ループ追加、サマリー更新 |
| `CLAUDE.md` | 編集 | pr-quant 追加、エージェント数更新 |

---

## 実装順序

| Wave | ファイル | 依存関係 |
|------|---------|---------|
| 1 | `.claude/agents/pr-quant.md`（新規作成） | なし |
| 1 | `.claude/skills/review-pr/SKILL.md`（pr-quant統合 + スコア出力変更） | なし |
| 2 | `.claude/skills/issue-implement-single/SKILL.md`（Phase 5.5追加） | なし（pr-*は既存） |
| 2 | `.claude/skills/issue-implementation-serial/SKILL.md`（レビュー修正ループ追加） | Wave 1（review-prの更新が必要） |
| 3 | `CLAUDE.md`（インデックス更新） | Wave 1, 2 |

---

## 検証方法

1. **Phase 5.5 の動作確認**: Python Issue を `/issue-implement` で実装し、Phase 5.5 が実行され、問題発見時に自動修正されることを確認
2. **pr-quant の起動確認**: クオンツ関連ファイル（src/strategy/ 等）を含むPRで `/review-pr` を実行し、pr-quant が起動することを確認
3. **pr-quant の非起動確認**: クオンツ関連ファイルを含まないPRで `/review-pr` を実行し、pr-quant が起動しないことを確認
4. **レビュー修正ループの確認**: 複数Issue の `/issue-implement` でPR作成後にレビュー → 修正 → 再レビューのループが実行されることを確認
5. **サマリー出力確認**: サマリーに incremental_review（各Issue）と PRレビュー修正履歴が含まれることを確認
