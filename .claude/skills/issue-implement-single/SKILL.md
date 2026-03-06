---
name: issue-implement-single
description: |
  単一の GitHub Issue を実装するスキル（コンテキスト分離）。
  context: fork により分離されたコンテキストで実行される。
  Python/Agent/Command/Skill の4つの開発タイプに対応。
context: fork
agent: general-purpose
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

# Issue Implement Single

単一の GitHub Issue を分離されたコンテキストで実装するスキルです。

## 重要: このスキルは context: fork で実行される

- 親のコンテキストから分離された環境で実行されます
- 実装の詳細は親に返りません（サマリーのみ）
- 複数Issue連続実装時のコンテキスト増大を防ぎます

---

## 入力

```
$ARGUMENTS = <issue_number> [--skip-pr]
```

- `issue_number`: 実装する GitHub Issue 番号（必須）
- `--skip-pr`: PR作成をスキップ（複数Issue連続実装時に使用）

---

## 🚨 必須ルール: Task ツールによるサブエージェント起動

**直接コードを書くことは絶対に禁止です。**

Python ワークフローでは、各 Phase で必ず **Task ツール**を使用してサブエージェントを起動してください。

### 禁止される行為

- Read/Write/Edit ツールで直接テストコードを書く
- Read/Write/Edit ツールで直接実装コードを書く
- サブエージェントを起動せずに Phase を完了したとみなす

### 必須の行為

各 Phase で Task ツールを呼び出し、以下のエージェントを起動すること：

| Phase | subagent_type | 用途 |
|-------|---------------|------|
| 1 | `test-writer` | テスト作成 |
| 2 | `pydantic-model-designer` | データモデル設計 |
| 3 | `feature-implementer` | TDD実装 |
| 4 | `code-simplifier` | コード整理 |
| 5 | `quality-checker` | 品質自動修正 |
| 5.5 | `pr-readability`, `pr-security-code`, `pr-test-coverage` | 簡易コードレビュー（3並列） |

### 判定基準

Task ツールを使わずに直接実装した場合、そのワークフローは **失敗** とみなします。

---

## 対応する開発タイプ

| タイプ | 対象 | ワークフロー |
|--------|------|--------------|
| `python` | Pythonコード開発 | テスト作成→データモデル設計→実装→コード整理→品質保証→コミット |
| `agent` | エージェント開発 | agent-creator に委譲→コミット |
| `command` | コマンド開発 | command-expert に委譲→コミット |
| `skill` | スキル開発 | skill-creator に委譲→コミット |

---

## 処理フロー

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: Issue検証・タイプ判定                               │
│    ├─ gh issue view {number} で情報取得                     │
│    ├─ チェックリスト抽出                                     │
│    └─ 開発タイプ判定（ラベル/キーワード）                    │
│                                                             │
│ Phase 0.5: 外部API調査（条件付き） ← NEW                     │
│    ├─ Issue内容から外部ライブラリ使用を検出                 │
│    ├─ 検出時: Task(api-usage-researcher) で調査実行         │
│    ├─ 未検出時: スキップして Phase 1 へ                     │
│    └─ 調査結果(api_research)を後続Phaseに受け渡し           │
│                                                             │
│ タイプ別ワークフロー実行                                     │
│    │                                                        │
│    ├─ Python: Phase 1-5                                     │
│    │  ├─ Task(test-writer) でテスト作成（Red）              │
│    │  │     └─ api_research 結果を参照                      │
│    │  ├─ Task(pydantic-model-designer) でモデル設計         │
│    │  │     └─ api_research 結果を参照                      │
│    │  ├─ Task(feature-implementer) で実装                   │
│    │  │     └─ api_research 結果を参照                      │
│    │  ├─ Task(code-simplifier) でコード整理                 │
│    │  └─ Task(quality-checker) で品質保証                   │
│    │                                                        │
│    │  Phase 5.5: 簡易コードレビュー（常に実行）            │
│    │  ├─ git diff HEAD で差分取得                          │
│    │  ├─ 3並列: Task(pr-readability), Task(pr-security-code), │
│    │  │         Task(pr-test-coverage)                     │
│    │  │   └─ HIGH/CRITICAL のみ報告                        │
│    │  ├─ 問題なし → Phase 6 へ                             │
│    │  └─ 問題あり → 修正 → quality-checker --quick         │
│    │       └─ 最大2サイクル、修正不可は警告で続行          │
│    │                                                        │
│    └─ Agent/Command/Skill:                                  │
│       └─ Task(xxx-creator/expert) に全委譲                  │
│                                                             │
│ 🚨 Phase 6: コミット前検証（必須）                           │
│    ├─ make check-all を実行                                 │
│    ├─ 失敗時: エラー詳細を出力して処理中断                  │
│    └─ 成功時: コミット作成へ進む                            │
│                                                             │
│ コミット作成（Phase 6 成功時のみ）                          │
│    └─ git commit -m "feat: ... Fixes #{number}"             │
│                                                             │
│ PR作成（--skip-pr でない場合のみ）                          │
│    └─ gh pr create ...                                      │
│                                                             │
│ Phase 6.5: PR設計レビュー（PR作成時のみ、--skip-pr 時は省略）│
│    ├─ Task(pr-design) でSOLID原則・DRY・抽象化を検証        │
│    ├─ 重大な問題あり: 警告を出力（CI前に修正推奨）          │
│    └─ 問題なし: Phase 7 へ進む                              │
│                                                             │
│ 🚨 Phase 7: CIチェック検証（PR作成時のみ、--skip-pr 時は省略）│
│    ├─ gh pr checks --watch --fail-fast で完了待ち           │
│    ├─ 全パス: 作業完了                                      │
│    └─ 失敗: エラー修正→再プッシュ→再検証（最大3回）        │
│                                                             │
│ サマリー出力（親に返却される情報）                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 開発タイプ判定ロジック

```yaml
判定順序:
  1. ラベルによる判定（優先）:
     - "agent" | "エージェント" → agent
     - "command" | "コマンド" → command
     - "skill" | "スキル" → skill
     - 上記以外 → python

  2. キーワード判定（ラベルなし時）:
     - ".claude/agents/" パスへの言及 → agent
     - ".claude/commands/" パスへの言及 → command
     - ".claude/skills/" パスへの言及 → skill
     - 上記以外 → python
```

---

## サブエージェント連携

### Python ワークフロー

| Phase | subagent_type | prompt に含める情報 |
|-------|---------------|---------------------|
| 0.5 | `api-usage-researcher` | Issue情報、受け入れ条件（**条件付き実行**） |
| 1 | `test-writer` | Issue情報、受け入れ条件、対象パッケージ、**api_research結果** |
| 2 | `pydantic-model-designer` | Issue情報、Phase 1のテストファイル、**api_research結果** |
| 3 | `feature-implementer` | Issue番号、ライブラリ名、Phase 2のモデル、**api_research結果** |
| 4 | `code-simplifier` | 変更されたファイル一覧 |
| 5 | `quality-checker` | --auto-fix モード |
| 5.5 | `pr-readability`, `pr-security-code`, `pr-test-coverage` | 変更差分（git diff HEAD）、HIGH/CRITICALのみ報告指示 |
| 6 | **直接実行** | `make check-all` でコミット前検証 |

### Agent/Command/Skill ワークフロー

| タイプ | subagent_type | 備考 |
|--------|---------------|------|
| agent | `agent-creator` | 要件分析→設計→実装→検証を一括実行 |
| command | `command-expert` | コマンド設計→作成 |
| skill | `skill-creator` | 要件分析→設計→実装→検証を一括実行 |

---

## Phase 0.5: 外部API調査（条件付き）

Phase 0 完了後、Issue 内容に外部APIの使用が検出された場合のみ実行。

### 実行条件

Issue本文・ラベル・受け入れ条件から以下を検出した場合に実行:

```yaml
高信頼度キーワード:
  - yfinance, yf.Ticker, yf.download
  - requests, httpx, aiohttp
  - pandas, pd.DataFrame
  - numpy, np.array
  - pydantic, BaseModel
  - curl_cffi
  - fredapi, fred
  - sec-api, edgar
  - openai, anthropic

中信頼度パターン:
  - import文への言及
  - pip install / uv add への言及
  - 外部API・認証・rate limiting への言及
```

### サブエージェント呼び出し

```yaml
subagent_type: api-usage-researcher
prompt: |
  Issue #{issue_number} の外部API調査を実行してください。

  ## Issue情報
  - タイトル: {issue_title}
  - 本文: {issue_body}
  - ラベル: {issue_labels}
  - 受け入れ条件: {acceptance_criteria}
```

### 出力の後続 Phase への受け渡し

`api_research` 結果（JSON）を Phase 1, 2, 3 のプロンプトに含める:

```yaml
Phase 1 (test-writer):
  追加情報: |
    ## 外部API調査結果
    ```json
    {api_research}
    ```
    - 検出されたライブラリのAPIを使用するテストを作成してください
    - best_practices に従ってください

Phase 2 (pydantic-model-designer):
  追加情報: |
    ## 外部API調査結果
    ```json
    {api_research}
    ```
    - return_type を参考にモデルを設計してください

Phase 3 (feature-implementer):
  追加情報: |
    ## 外部API調査結果
    ```json
    {api_research}
    ```
    - apis_to_use の usage_pattern に従って実装してください
    - project_patterns の既存実装を参考にしてください
    - 追加のContext7調査は不要です（調査済み）
```

### スキップ時

外部ライブラリが検出されなかった場合:

```yaml
api_research:
  investigation_needed: false
  detection_confidence: none

後続Phase:
  - api_research の参照をスキップ
  - 通常のワークフローを実行
```

---

## Phase 5.5: 簡易コードレビュー（常に実行）

**Phase 5（quality-checker --auto-fix）の後、Phase 6（make check-all）の前に実行。`--skip-pr` でも常に実行する。**

### 使用エージェント（3並列）

| エージェント | チェック内容 | 選定理由 |
|---|---|---|
| `pr-readability` | 命名規則・型ヒント・Docstring | 軽量、規約違反の早期発見 |
| `pr-security-code` | OWASP A01-A05・機密情報検出 | セキュリティ脆弱性は早期発見が重要 |
| `pr-test-coverage` | テスト存在・カバレッジ・エッジケース | TDD原則によるテスト網羅性確認 |

### 差分ベース入力

```bash
# 未コミットの変更（Phase 5.5 はコミット前に実行）
git diff HEAD               # 差分内容
git diff HEAD --name-only   # 変更ファイル一覧
```

### プロンプト方針

各エージェントに対し **HIGH/CRITICAL のみ報告** を指示:

```
簡易レビューモード（Issue実装後の差分のみ対象）。
HIGH/CRITICAL の問題のみ報告してください。MEDIUM/LOW は省略。
```

### 自動修正フロー

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

### 出力フォーマット

```yaml
incremental_review:
  status: passed | fixed | failed
  agents_run: 3
  issues_found: { critical: 0, high: 0 }
  issues_fixed: { critical: 0, high: 0 }
  issues_remaining: []  # status == failed の場合のみ
  fix_cycles: 0
```

---

## 🚨 Phase 6: コミット前検証（必須）

**コミット前に `make check-all` を実行し、成功した場合のみコミットを作成する。**

この検証により、CI で発生するエラーを事前に防止します。

### 実行手順

```bash
# 1. make check-all を実行
make check-all

# 2. 終了コードを確認
# - 0: 成功 → コミット作成へ進む
# - 非0: 失敗 → エラー詳細を出力して処理中断
```

### 失敗時の対応

`make check-all` が失敗した場合:

1. **エラー内容を詳細に出力**
   ```yaml
   phase6_failure:
     format: [PASS/FAIL]
     lint: [PASS/FAIL] - エラー詳細
     typecheck: [PASS/FAIL] - エラー詳細
     test: [PASS/FAIL] - 失敗したテスト一覧
   ```

2. **処理を中断**（コミットは作成しない）

3. **サマリーにエラー情報を含めて返却**

### 成功時の対応

`make check-all` が成功した場合:

1. **成功ログを出力**
   ```
   ✅ Phase 6: コミット前検証成功
   - format: PASS
   - lint: PASS
   - typecheck: PASS
   - test: PASS (XX tests)
   ```

2. **コミット作成へ進む**

### 重要: 検証をスキップしない

以下の理由により、Phase 6 の検証は**絶対にスキップしてはいけない**:

- CI でのエラーを事前に防止
- pre-commit フックはテストを含まない
- quality-checker の修正後に新たな問題が発生する可能性がある

---

## Phase 6.5: PR設計レビュー（PR作成時のみ）

**PR作成後（`--skip-pr` でない場合）、CIチェック前にコード設計品質を検証する。**

`--skip-pr` の場合は、親スキル（issue-implementation-serial）がPR作成後に検証するため、このPhaseはスキップする。

### 実行手順

#### 6.5.1 pr-design サブエージェントの呼び出し

```yaml
subagent_type: "pr-design"
description: "PR design review"
prompt: |
  PR #{pr_number} のコード設計品質を検証してください。

  ## 検証対象PR
  - PR番号: {pr_number}
  - Issue: #{issue_number}

  ## 検証観点
  - SOLID原則（単一責任・開放閉鎖・リスコフ置換・IF分離・依存性逆転）
  - DRY原則（重複コード検出）
  - 抽象化レベルの一貫性
```

#### 6.5.2 レビュー結果の確認

pr-design の出力を確認し、重大な問題がある場合は警告を出力:

```yaml
design_review:
  score: 85  # 0-100
  solid_compliance:
    single_responsibility: "PASS"
    open_closed: "WARN"  # ← 警告あり
    ...
  issues:
    - severity: "HIGH"
      category: "solid"
      description: "if文の連鎖が検出されました"
      recommendation: "Strategy パターンへの置き換えを検討してください"
```

**判定基準**:

| スコア | 判定 | アクション |
|--------|------|-----------|
| 90-100 | 優秀 | Phase 7 へ進む |
| 70-89 | 良好 | 警告を出力、Phase 7 へ進む |
| 50-69 | 要改善 | **警告を出力、修正推奨（Phase 7 前に修正可能）** |
| 0-49 | 問題あり | **重大な警告を出力、修正推奨（Phase 7 前に修正可能）** |

#### 6.5.3 問題ありの場合

重大な問題（スコア50未満、または CRITICAL/HIGH の issue）がある場合:

1. **警告を出力**
   ```
   ⚠️ Phase 6.5: PR設計レビューで問題を検出

   スコア: 45/100

   重大な問題:
   - [HIGH] SOLID: if文の連鎖が検出されました
     → Strategy パターンへの置き換えを検討してください

   推奨: CIチェック前にこれらの問題を修正してください。
   修正しない場合は、そのままCIチェックに進みます。
   ```

2. **ユーザーに確認**（オプション）
   - 修正してから CI へ進む
   - そのまま CI へ進む（レビュー指摘事項として記録）

3. **Phase 7 へ進む**

#### 重要: レビュー結果は CI ブロックしない

pr-design のレビュー結果は**警告のみ**で、CI チェックはブロックしません。設計品質の問題は PR レビュー時にコメントとして残すことで、継続的な改善を促します。

---

## 🚨 Phase 7: CIチェック検証（PR作成時のみ）

**PR作成後（`--skip-pr` でない場合）、GitHub Actions の CIチェックが全てパスするまで作業を完了としない。**

`--skip-pr` の場合は、親スキル（issue-implementation-serial）がPR作成後にCIチェックを検証するため、このPhaseはスキップする。

### 実行手順

#### 7.1 CIチェックの完了待ち

```bash
# CIチェックの完了を待つ（最大10分）
gh pr checks <pr-number> --watch --fail-fast
```

#### 7.2 CIチェック結果の確認

```bash
gh pr checks <pr-number> --json name,state,bucket,description
```

#### 7.3 全チェックがパスした場合

→ 作業完了としてサマリーを出力

#### 7.4 いずれかのチェックが失敗した場合

1. **失敗したチェックのログを確認**
   ```bash
   gh run view <run-id> --log-failed
   ```

2. **エラー原因を分析し修正を実施**

3. **修正をコミット・プッシュ**
   ```bash
   git add <修正ファイル>
   git commit -m "fix: CI エラーを修正"
   git push
   ```

4. **再度CIチェックを検証（7.1 に戻る）**
   - 最大3回まで修正→再検証を繰り返す
   - 3回失敗した場合はエラーサマリーを返却

---

## コミットメッセージ形式

```bash
git commit -m "$(cat <<'EOF'
feat(<scope>): <変更内容の要約>

<詳細説明>

Fixes #<issue_number>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## 出力フォーマット（親に返却されるサマリー）

### 成功時

```yaml
status: success
issue:
  number: 123
  title: "ユーザー認証機能の追加"
  type: python
implementation:
  files_created:
    - src/finance/auth/authenticator.py
    - tests/finance/unit/auth/test_authenticator.py
  files_modified:
    - src/finance/__init__.py
pre_commit_validation:  # Phase 6 の結果
  status: passed
  format: PASS
  lint: PASS
  typecheck: PASS
  test: PASS (15 tests)
incremental_review:  # Phase 5.5 の結果
  status: passed
  agents_run: 3
  issues_found: { critical: 0, high: 0 }
  issues_fixed: { critical: 0, high: 0 }
  fix_cycles: 0
commit:
  hash: "abc1234"
  message: "feat(auth): ユーザー認証機能を追加"
pr:
  number: 456  # --skip-pr の場合は null
  url: "https://github.com/YH-05/finance/pull/456"
design_review:  # Phase 6.5 の結果（PR作成時のみ、--skip-pr の場合は null）
  score: 85
  solid_compliance:
    single_responsibility: "PASS"
    open_closed: "PASS"
    liskov_substitution: "PASS"
    interface_segregation: "PASS"
    dependency_inversion: "PASS"
  issues_found: 0
ci_checks:  # Phase 7 の結果（PR作成時のみ、--skip-pr の場合は null）
  status: passed
  checks:
    - name: "check-all"
      state: "pass"
  fix_attempts: 0  # CI修正の試行回数
```

### 失敗時（Phase 6 コミット前検証失敗）

```yaml
status: failed
issue:
  number: 123
  title: "ユーザー認証機能の追加"
  type: python
error:
  phase: 6
  message: "コミット前検証（make check-all）が失敗しました"
  details: |
    format: PASS
    lint: FAIL - src/finance/auth/authenticator.py:15: F401 unused import
    typecheck: PASS
    test: FAIL - test_正常系_認証成功 で AssertionError
pre_commit_validation:
  status: failed
  format: PASS
  lint: FAIL
  typecheck: PASS
  test: FAIL
partial_commit:
  hash: null  # コミットは作成されていない
```

### 失敗時（その他のPhase）

```yaml
status: failed
issue:
  number: 123
  title: "ユーザー認証機能の追加"
  type: python
error:
  phase: 3
  message: "feature-implementer がテストを通せませんでした"
  details: "test_正常系_認証成功 で AssertionError"
partial_commit:
  hash: null  # コミット前に失敗した場合
```

---

## エラーハンドリング

| Phase | エラー | 対処 |
|-------|--------|------|
| 0 | Issue not found | 処理中断、エラーサマリーを返却 |
| 0 | Issue closed | 処理中断、エラーサマリーを返却 |
| 1 | Test creation failed | 最大3回リトライ |
| 2 | Model design failed | 要件を再確認、シンプルなモデルから開始 |
| 3 | Implementation failed | タスク分割して再試行 |
| 4 | Code simplification failed | 変更対象を絞って再試行 |
| 5 | Quality check failed | 自動修正（最大5回） |
| 5.5 | Review found issues | 自動修正（最大2サイクル）、修正不可は警告で続行 |
| 6 | **make check-all failed** | **処理中断、コミットしない、エラー詳細を返却** |
| 7 | **CIチェック失敗** | **エラー修正→再プッシュ→再検証（最大3回）** |
| 7 | **CI修正不可（3回失敗）** | **失敗詳細をサマリーに含めて返却** |

---

## 完了条件

### Python ワークフロー

- [ ] Phase 0: Issue情報が取得でき、開発タイプが判定
- [ ] Phase 1: Task(test-writer) でテストがRed状態で作成
- [ ] Phase 2: Task(pydantic-model-designer) でモデルが作成
- [ ] Phase 3: Task(feature-implementer) で全タスクが実装
- [ ] Phase 4: Task(code-simplifier) でコード整理が完了
- [ ] Phase 5: Task(quality-checker) で品質自動修正が完了
- [ ] **Phase 5.5: 3エージェント並列の簡易コードレビューが完了（HIGH/CRITICALは修正済み）**
- [ ] **Phase 6: `make check-all` が成功（コミット前検証）**
- [ ] コミットが作成されている（Phase 6 成功後のみ）
- [ ] **Phase 6.5: Task(pr-design) でPR設計レビューが完了（`--skip-pr` でない場合のみ）**
- [ ] **Phase 7: PR作成後のCIチェックが全てパス（`--skip-pr` でない場合のみ）**
- [ ] サマリーが出力されている

### Agent/Command/Skill ワークフロー

- [ ] Phase 0: Issue情報が取得でき、開発タイプが判定
- [ ] Task(xxx-creator/expert) で開発が完了
- [ ] **`make check-all` が成功（コミット前検証）**
- [ ] コミットが作成されている（検証成功後のみ）
- [ ] **Task(pr-design) でPR設計レビューが完了（`--skip-pr` でない場合のみ）**
- [ ] **PR作成後のCIチェックが全てパス（`--skip-pr` でない場合のみ）**
- [ ] サマリーが出力されている

---

## 関連スキル

- **issue-implementation-serial**: 複数Issue連続実装（このスキルを繰り返し呼び出す）
- **tdd-development**: TDD開発のナレッジベース
- **agent-expert**: エージェント設計のナレッジベース
- **skill-expert**: スキル設計のナレッジベース
