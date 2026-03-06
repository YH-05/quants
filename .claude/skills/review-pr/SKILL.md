---
name: review-pr
description: PRレビュー（コード品質・セキュリティ・テスト）。最大8つのサブエージェントを並列実行してPRを多角的にレビューし、フィードバックを提供する。
allowed-tools: Read, Bash, Task
---

# PR Review Skill

> **役割の明確化**: このスキルは**PRの包括的レビュー**に特化しています。
>
> - コード品質の自動修正 → `/ensure-quality`
> - 詳細な分析レポート → `/analyze`
> - セキュリティ検証のみ → `/scan`

## 目的

Pull Requestの変更内容を多角的にレビューし、フィードバックを提供します。
最大8つのサブエージェントを並列実行し、コード品質・セキュリティ・テストの3つの観点から包括的なレビューを実施します。

## いつ使用するか

### プロアクティブ使用

このスキルは以下の状況で自動的に使用を検討してください：

1. **PR作成後のレビュー依頼**
   - 「PRをレビューして」
   - 「コードレビューをお願い」

2. **マージ前の品質確認**
   - 「マージ前にチェックして」
   - 「品質に問題ないか確認して」

### 明示的な使用

- `/review-pr` コマンド
- 「PRの包括的レビュー」などの直接的な要求

## レビュー対象の決定

- **GitHub PRがある場合**: PR情報を取得してレビュー
- **PRがない場合**: ローカル差分（main...HEAD）をレビュー
- **エラーケース**:
  - PRなし かつ mainブランチ上 → エラーメッセージを表示して終了
  - 差分なし → 「変更がありません」と報告して終了

## プロセス

### ステップ 1: PR/差分の取得

#### 1.1 GitHub PRの確認

```bash
# PRが存在するか確認
gh pr view --json number,title,body,files,additions,deletions,baseRefName,headRefName 2>/dev/null
```

**PRがある場合**:
- PR情報（タイトル、説明、変更ファイル）を取得
- `gh pr diff` で差分を取得

**PRがない場合**:
- ローカル差分モードに切り替え
- `git diff main...HEAD` で差分を取得
- `git diff main...HEAD --name-only` で変更ファイルリストを取得

#### 1.2 エラーチェック

- PRなし かつ mainブランチ上 → エラーメッセージを表示して終了
- 差分なし → 「変更がありません」と報告して終了

### ステップ 2: マルチサブエージェントレビュー（並列実行）

**7つのサブエージェント**を**並列**で起動してレビューを実行します。

#### エージェント構成

| グループ | エージェント | 担当領域 | 条件 |
|---------|------------|---------|------|
| コード品質 | pr-readability | 可読性・命名規則・Docstring・型ヒント | 常時 |
| コード品質 | pr-design | SOLID原則・DRY・抽象化レベル | 常時 |
| コード品質 | pr-performance | アルゴリズム複雑度・メモリ効率・I/O | 常時 |
| コード品質 | **pr-quant** | **数値精度・ベクトル化・バックテスト・リスク指標** | **クオンツファイル変更時のみ** |
| セキュリティ | pr-security-code | OWASP A01-A05（コード脆弱性） | 常時 |
| セキュリティ | pr-security-infra | OWASP A06-A10 + 依存関係監査 | 常時 |
| テスト | pr-test-coverage | テスト有無・カバレッジ・エッジケース | 常時 |
| テスト | pr-test-quality | テスト品質・独立性・再現性 | 常時 |

#### pr-quant の起動条件

変更ファイルが以下のパスに含まれる場合のみ起動:

```python
QUANT_PATHS = [
    "src/strategy/", "src/factor/", "src/analyze/",
    "src/market/", "src/dev/ca_strategy/",
    "tests/strategy/", "tests/factor/", "tests/analyze/",
    "tests/market/", "tests/ca_strategy/",
]
```

変更ファイルリストとパスを照合し、一致するファイルがあれば pr-quant を起動する。一致しない場合はスキップ。

#### 2.1 コード品質グループ（3並列 + 条件付き1）

##### pr-readability（可読性）

```yaml
subagent_type: "pr-readability"
description: "PR readability review"
prompt: |
  PRの変更コードの可読性をレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点
  1. 命名規則（PascalCase/snake_case/UPPER_SNAKE）
  2. 型ヒントカバレッジ（目標90%以上）
  3. Docstringカバレッジ（目標80%以上）
  4. コメントの品質

  ## 出力
  pr_readability 形式のYAMLを出力
```

##### pr-design（設計）

```yaml
subagent_type: "pr-design"
description: "PR design review"
prompt: |
  PRの変更コードの設計品質をレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点
  1. SOLID原則（S/O/L/I/D）
  2. DRY原則（重複コード検出）
  3. 抽象化レベルの一貫性
  4. 設計パターンの適用

  ## 出力
  pr_design 形式のYAMLを出力
```

##### pr-performance（パフォーマンス）

```yaml
subagent_type: "pr-performance"
description: "PR performance review"
prompt: |
  PRの変更コードのパフォーマンスをレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点
  1. サイクロマティック複雑度
  2. アルゴリズム効率（O(n²)検出）
  3. メモリ効率
  4. I/O最適化・キャッシング機会

  ## 出力
  pr_performance 形式のYAMLを出力
```

##### pr-quant（クオンツ計算品質 - 条件付き起動）

**起動条件**: 変更ファイルが `QUANT_PATHS` に含まれる場合のみ起動。

```yaml
subagent_type: "pr-quant"
description: "PR quant computing review"
prompt: |
  PRの変更コードのクオンツ計算品質をレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト（クオンツ関連のみ）]

  ## 差分
  [git diff の内容]

  ## レビュー観点（QC-01 ~ QC-08）
  1. QC-01: 浮動小数点の == 比較禁止（epsilon or pytest.approx）
  2. QC-02: 単利年率化禁止（複利必須）
  3. QC-03: バックテストの前方参照（PoiT違反）
  4. QC-04: pandas/NumPy 集計での Python ループ禁止
  5. QC-05: 数値計算関数の Hypothesis テスト不足
  6. QC-06: リスク指標のゼロ除算防御欠如
  7. QC-07: スキーマ検証なしのデータ永続化
  8. QC-08: データ量/パターンに基づかない DB 選択

  ## 出力
  pr_quant 形式のYAMLを出力
```

#### 2.2 セキュリティグループ（2並列）

##### pr-security-code（コードセキュリティ）

```yaml
subagent_type: "pr-security-code"
description: "PR code security review"
prompt: |
  PRの変更コードをセキュリティ観点でレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点（OWASP A01-A05）
  1. A01: アクセス制御の不備
  2. A02: 暗号化の失敗
  3. A03: インジェクション
  4. A04: 安全でない設計
  5. A05: セキュリティの設定ミス
  6. 機密情報のハードコード検出

  ## 出力
  pr_security_code 形式のYAMLを出力
```

##### pr-security-infra（インフラセキュリティ）

```yaml
subagent_type: "pr-security-infra"
description: "PR infra security review"
prompt: |
  PRの変更をインフラセキュリティ観点でレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点（OWASP A06-A10）
  1. A06: 脆弱で古いコンポーネント
  2. A07: 識別と認証の失敗
  3. A08: ソフトウェアとデータの整合性の失敗
  4. A09: セキュリティログとモニタリングの失敗
  5. A10: SSRF
  6. 依存関係の脆弱性監査

  ## 出力
  pr_security_infra 形式のYAMLを出力
```

#### 2.3 テストグループ（2並列）

##### pr-test-coverage（カバレッジ）

```yaml
subagent_type: "pr-test-coverage"
description: "PR test coverage review"
prompt: |
  PRの変更に対するテストカバレッジをレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点
  1. テストの存在確認
  2. カバレッジ評価（GOOD/FAIR/POOR）
  3. エッジケース網羅性
  4. 分岐カバレッジ

  ## 出力
  pr_test_coverage 形式のYAMLを出力
```

##### pr-test-quality（品質）

```yaml
subagent_type: "pr-test-quality"
description: "PR test quality review"
prompt: |
  PRのテストコードの品質をレビューしてください。

  ## 対象ファイル
  [変更ファイルリスト]

  ## 差分
  [git diff の内容]

  ## レビュー観点
  1. テスト命名の品質
  2. アサーションの適切性
  3. モック使用の適切性
  4. テスト独立性・再現性

  ## 出力
  pr_test_quality 形式のYAMLを出力
```

### ステップ 3: レビュー結果の統合と出力

7つのサブエージェントからの結果を**3カテゴリ**に統合して出力を生成します。

#### 結果統合ロジック

```yaml
# スコア統合方針
# 加重平均を廃止し、各エージェントのスコア（0-100）をそのまま出力する。
# どの観点が弱いか一目でわかるようにする。
scores:
  code_quality:
    readability: 0   # pr-readability のスコア（0-100）
    design: 0        # pr-design のスコア（0-100）
    performance: 0   # pr-performance のスコア（0-100）
    quant: null      # pr-quant のスコア（0-100）、クオンツファイル変更時のみ値が入る

  security:
    code: 0          # pr-security-code のスコア（0-100）
    infra: 0         # pr-security-infra のスコア（0-100）

  test:
    coverage: 0      # pr-test-coverage のスコア（0-100）
    quality: 0       # pr-test-quality のスコア（0-100）

# 問題統合方針
issues_merge:
  code_quality:
    - pr-readability.issues → naming, type_hints, docstrings
    - pr-design.issues → solid, dry, abstraction
    - pr-performance.issues → algorithm, memory, io
    - pr-quant.issues → numerical_precision, vectorization, backtesting, risk_metrics（条件付き）

  security:
    - pr-security-code.findings → A01-A05, secrets
    - pr-security-infra.findings → A06-A10, dependencies

  test:
    - pr-test-coverage.missing_tests → 欠落テスト
    - pr-test-quality.issues → 品質問題
```

#### 3.1 マークダウン出力（ターミナル標準出力）

```markdown
# PR レビュー結果

## PR情報
- **タイトル**: [PRタイトル]
- **ブランチ**: [base] <- [head]
- **変更ファイル数**: [数]
- **追加行数**: [数] / **削除行数**: [数]

## 総合評価

### コード品質
| 観点 | スコア | 評価 |
|------|--------|------|
| 可読性 | [0-100] | [評価] |
| 設計 | [0-100] | [評価] |
| パフォーマンス | [0-100] | [評価] |
| クオンツ計算 | [0-100 or N/A] | [評価] |

### セキュリティ
| 観点 | スコア | 評価 |
|------|--------|------|
| コードセキュリティ | [0-100] | [評価] |
| インフラセキュリティ | [0-100] | [評価] |

### テスト
| 観点 | スコア | 評価 |
|------|--------|------|
| カバレッジ | [0-100] | [評価] |
| テスト品質 | [0-100] | [評価] |

評価基準: 80+ 良好 / 60-79 改善推奨 / 60未満 要対応

## コード品質レビュー

### 良い点
- [良い点1]
- [良い点2]

### 改善が必要な点

#### [必須] 重大な問題
- **ファイル**: `[パス]:[行番号]`
- **問題**: [説明]
- **推奨修正**: [修正案]

#### [推奨] 改善提案
- [改善提案1]
- [改善提案2]

## セキュリティレビュー

### 検出された問題
| 重大度 | 件数 |
|--------|------|
| CRITICAL | [数] |
| HIGH | [数] |
| MEDIUM | [数] |
| LOW | [数] |

### 詳細
- **ID**: SEC-001
- **重大度**: [CRITICAL/HIGH/MEDIUM/LOW]
- **ファイル**: `[パス]:[行番号]`
- **問題**: [説明]
- **推奨修正**: [修正案]

## テストレビュー

### カバレッジ評価
- 変更コードのテストカバレッジ: [評価]
- エッジケースの網羅性: [評価]

### 不足しているテスト
- [テストケース1]
- [テストケース2]

## 推奨アクション

### 必須対応（マージ前に修正必要）
1. [アクション1]
2. [アクション2]

### 推奨対応（改善のため）
1. [アクション1]
2. [アクション2]

---
レビュー実行日時: [YYYY-MM-DD HH:MM:SS]
```

#### 3.2 YAMLレポート出力

**出力先**: `docs/pr-review/pr-review-YYYYMMDD-HHMMSS.yaml`

```yaml
# PRレビューレポート
# 生成日時: YYYY-MM-DD HH:MM:SS
# 生成スキル: review-pr

metadata:
  generated_at: "YYYY-MM-DD HH:MM:SS"
  pr_number: 123  # PRがある場合、なければnull
  pr_title: "[PRタイトル]"
  base_branch: "main"
  head_branch: "[ブランチ名]"
  review_mode: "remote"  # remote | local

pr_info:
  files_changed: 0
  additions: 0
  deletions: 0
  changed_files:
    - path: "[ファイルパス]"
      additions: 0
      deletions: 0

scores:
  code_quality:
    readability: 0   # 0-100
    design: 0        # 0-100
    performance: 0   # 0-100
    quant: null      # 0-100 or null（クオンツファイル変更時のみ）
  security:
    code: 0          # 0-100
    infra: 0         # 0-100
  test:
    coverage: 0      # 0-100
    quality: 0       # 0-100

code_quality:
  strengths:
    - "[良い点]"

  issues:
    critical: []
    high: []
    medium: []
    low: []

  solid_compliance:
    single_responsibility: "PASS"  # PASS/WARN/FAIL
    open_closed: "PASS"
    liskov_substitution: "PASS"
    interface_segregation: "PASS"
    dependency_inversion: "PASS"

security:
  vulnerability_count:
    critical: 0
    high: 0
    medium: 0
    low: 0

  findings:
    - id: "SEC-001"
      severity: "CRITICAL"
      category: "[カテゴリ]"
      location: "[ファイル]:[行番号]"
      description: "[問題の説明]"
      recommendation: "[修正案]"
      cwe_id: "CWE-XX"

test:
  coverage_assessment: "GOOD"  # GOOD/FAIR/POOR
  edge_cases_covered: true
  missing_tests: []

  test_quality:
    isolation: "PASS"  # PASS/WARN/FAIL
    reproducibility: "PASS"
    readability: "PASS"

recommended_actions:
  required:  # マージ前に必須
    - priority: 1
      action: "[アクション]"
      related_issues: []

  suggested:  # 推奨
    - priority: 1
      action: "[アクション]"

summary:
  verdict: "APPROVE"  # APPROVE/REQUEST_CHANGES/COMMENT
  comment: "[総合コメント]"
```

#### 3.3 GitHub PRコメント投稿（PRがある場合のみ）

```bash
gh pr review --comment --body "$(cat <<'EOF'
## PR レビュー結果

### 総合評価

#### コード品質
| 観点 | スコア | 評価 |
|------|--------|------|
| 可読性 | [0-100] | [評価] |
| 設計 | [0-100] | [評価] |
| パフォーマンス | [0-100] | [評価] |
| クオンツ計算 | [0-100 or N/A] | [評価] |

#### セキュリティ
| 観点 | スコア | 評価 |
|------|--------|------|
| コード | [0-100] | [評価] |
| インフラ | [0-100] | [評価] |

#### テスト
| 観点 | スコア | 評価 |
|------|--------|------|
| カバレッジ | [0-100] | [評価] |
| 品質 | [0-100] | [評価] |

### 主要な発見事項

#### 改善が必要な点
- [問題1の要約]
- [問題2の要約]

#### 良い点
- [良い点1]
- [良い点2]

### 推奨アクション
1. [最優先アクション]
2. [次のアクション]

---
Automated review by Claude Code
EOF
)"
```

### ステップ 4: 完了報告

レビュー完了をユーザーに報告:

1. マークダウンをターミナルに出力
2. YAMLファイルの保存場所を通知
3. GitHubコメントの投稿結果を通知（PRがある場合）

## エラーハンドリング

| 状況 | 対処 |
|------|------|
| PRなし + mainブランチ上 | 「レビュー対象がありません。feature ブランチで実行してください」と表示 |
| gh コマンド利用不可 | ローカルモードで続行し、GitHub コメント投稿をスキップ |
| 差分なし | 「変更がありません」と報告して終了 |
| サブエージェントエラー | 部分的な結果を出力し、エラーを報告 |

## エージェント一覧

| エージェント | モデル | 役割 | 条件 |
|------------|-------|------|------|
| pr-readability | sonnet | 可読性・命名・型ヒント・Docstring | 常時 |
| pr-design | sonnet | SOLID・DRY・抽象化レベル | 常時 |
| pr-performance | sonnet | 複雑度・アルゴリズム・メモリ・I/O | 常時 |
| pr-quant | sonnet | 数値精度・ベクトル化・バックテスト・リスク指標 | クオンツファイル変更時のみ |
| pr-security-code | sonnet | OWASP A01-A05・機密情報 | 常時 |
| pr-security-infra | sonnet | OWASP A06-A10・依存関係監査 | 常時 |
| pr-test-coverage | sonnet | テスト有無・カバレッジ・エッジケース | 常時 |
| pr-test-quality | sonnet | テスト品質・独立性・再現性 | 常時 |

## 使用例

### 例1: GitHub PRのレビュー

**状況**: GitHub上にPRが存在し、レビューが必要

**入力**: このスキルを呼び出す

**処理**:
1. `gh pr view` でPR情報を取得
2. `gh pr diff` で差分を取得
3. 7つのサブエージェントを並列実行
4. 結果を統合してマークダウン + YAML レポートを生成
5. GitHub PRにコメント投稿

**期待される出力**:
```
# PR レビュー結果

## PR情報
- **タイトル**: Add user authentication
- **ブランチ**: main <- feature/auth
- **変更ファイル数**: 5
- **追加行数**: 120 / **削除行数**: 30

## 総合評価

### コード品質
| 観点 | スコア | 評価 |
|------|--------|------|
| 可読性 | 85 | 良好 |
| 設計 | 90 | 良好 |
| パフォーマンス | 80 | 良好 |
| クオンツ計算 | N/A | - |

### セキュリティ
| 観点 | スコア | 評価 |
|------|--------|------|
| コード | 75 | 改善推奨 |
| インフラ | 80 | 良好 |

### テスト
| 観点 | スコア | 評価 |
|------|--------|------|
| カバレッジ | 90 | 良好 |
| 品質 | 85 | 良好 |
...
```

---

### 例2: ローカル差分のレビュー

**状況**: PRは未作成だが、ローカルでfeatureブランチを作業中

**入力**: このスキルを呼び出す

**処理**:
1. `gh pr view` でPRを確認 → 存在しない
2. ローカルモードに切り替え
3. `git diff main...HEAD` で差分を取得
4. 7つのサブエージェントを並列実行
5. 結果を統合してマークダウン + YAML レポートを生成
6. GitHub PRコメント投稿はスキップ

**期待される出力**:
```
# PR レビュー結果（ローカルモード）

## 変更情報
- **ブランチ**: main <- feature/refactor-db
- **変更ファイル数**: 3
- **追加行数**: 45 / **削除行数**: 20

## 総合評価
...
```

---

### 例3: エラーケース（mainブランチ上）

**状況**: mainブランチ上で実行され、PRもない

**入力**: このスキルを呼び出す

**処理**:
1. `gh pr view` でPRを確認 → 存在しない
2. 現在のブランチを確認 → main
3. エラーメッセージを表示して終了

**期待される出力**:
```
エラー: レビュー対象がありません。
feature ブランチで実行するか、PRを作成してから実行してください。
```

---

### 例4: 差分なしのケース

**状況**: featureブランチだが、mainとの差分がない

**入力**: このスキルを呼び出す

**処理**:
1. `git diff main...HEAD` で差分を確認 → 差分なし
2. 「変更がありません」と報告して終了

**期待される出力**:
```
変更がありません。
コードの変更後に再度実行してください。
```

## 品質基準

### 必須（MUST）

- [ ] 最大8つのサブエージェントを並列実行（pr-quant はクオンツファイル変更時のみ）
- [ ] コード品質・セキュリティ・テストの3カテゴリで要素別スコア評価
- [ ] マークダウン出力をターミナルに表示
- [ ] YAMLレポートを `docs/pr-review/` に保存
- [ ] PRがある場合はGitHubにコメント投稿
- [ ] エラーケースを適切にハンドリング

### 推奨（SHOULD）

- レビュー結果のスコアを定量化（0-100）
- 問題を重大度別に分類（CRITICAL/HIGH/MEDIUM/LOW）
- 推奨アクションを優先度付き（必須/推奨）で提示
- OWASP Top 10に基づくセキュリティレビュー
- SOLID原則に基づく設計レビュー

## 出力フォーマット

### レビュー完了報告

```
================================================================================
                    PRレビュー完了
================================================================================

## レビュー結果
- コード品質: 可読性 {readability}/100, 設計 {design}/100, パフォーマンス {performance}/100, クオンツ {quant or N/A}/100
- セキュリティ: コード {code}/100, インフラ {infra}/100
- テスト: カバレッジ {coverage}/100, 品質 {quality}/100

## 出力ファイル
- マークダウン: ターミナルに出力済み
- YAMLレポート: docs/pr-review/pr-review-YYYYMMDD-HHMMSS.yaml

## GitHub PRコメント
- 投稿: ✓ 完了 / - スキップ（ローカルモード）

## 推奨アクション
必須対応: {count}件
推奨対応: {count}件

================================================================================
```

## 注意事項

- **最大8つのサブエージェント**が並列実行されるため、効率的に処理されます（pr-quant はクオンツファイル変更時のみ起動）
- レビューは詳細な分析のため、数分かかる場合があります
- セキュリティレビューは補完的なツールとして使用し、専門的なセキュリティ監査の代替にはなりません
- YAMLレポートは `docs/pr-review/` ディレクトリに日付・時刻付きで保存されます

## 完了条件

このスキルは以下の条件を満たした場合に完了とする：

- [ ] PR/差分の取得が成功
- [ ] 最大8つのサブエージェントの並列実行が成功
- [ ] 結果の統合が成功
- [ ] マークダウン出力が生成されている
- [ ] YAMLレポートが保存されている
- [ ] GitHubコメント投稿が成功（PRがある場合）
- [ ] ユーザーへの完了報告が実施されている

## 関連スキル

- **coding-standards**: コーディング規約（可読性レビューで参照）
- **tdd-development**: TDD開発プロセス（テストレビューで参照）
- **error-handling**: エラーハンドリングパターン（セキュリティレビューで参照）

## 参考資料

- `.claude/agents/pr-*/`: 8つのPRレビューエージェント（pr-quant は条件付き起動）
- `CLAUDE.md`: プロジェクト全体のガイドライン
- `docs/coding-standards.md`: コーディング規約詳細
- OWASP Top 10: https://owasp.org/www-project-top-ten/
