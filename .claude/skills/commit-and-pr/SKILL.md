---
name: commit-and-pr
description: "変更のコミットとPR作成を一括実行するスキル。/commit-and-pr コマンドで使用。品質確認、コミット、プッシュ、PR作成、CIチェックを自動化。"
allowed-tools: Read, Bash
---

# Commit and PR - 変更のコミットと PR 作成

現在の変更をコミットし、適切なブランチを作成してプルリクエストを作成します。CLAUDE.md の「GitHub 操作」セクションの規約に従います。

## 実行手順

### 1. 変更内容の確認

```bash
git status              # 変更ファイルの確認
git diff                # 変更内容の確認
git log --oneline -10   # 最近のコミット履歴を確認
```

### 2. コミットメッセージの作成

CLAUDE.md で定義されているフォーマットに従います：

```
<変更の種類>: <変更内容の要約>

詳細な説明（必要に応じて）

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### 3. ブランチ名の命名規則

変更の種類に応じて適切なプレフィックスを使用：

-   `feature/` - 機能追加
-   `fix/` - バグ修正
-   `refactor/` - リファクタリング
-   `docs/` - ドキュメント更新
-   `test/` - テスト追加・修正

### 4. ラベルの命名規則

PR に付けるラベル：

-   `enhancement` - 機能追加
-   `bug` - バグ修正
-   `refactor` - リファクタリング
-   `documentation` - ドキュメント
-   `test` - テスト

### 5. 実行ステップ

1. **変更内容の分析**

    - git status と git diff で変更を確認
    - 変更の種類を判断（feature/fix/refactor/docs/test）

2. **コード簡素化（自動実行）**

    - code-simplifier エージェントを起動
    - 変更されたファイルに対してコード整理を実行
    - 型ヒント、Docstring、命名規則、関数分割などを改善
    - 各修正後に自動的にテスト実行・検証

3. **品質確認（自動実行）**

    - quality-checker エージェント（--quick モード）を起動
    - format/lint/typecheck/test の自動修正
    - 問題があれば自動修正

4. **ブランチの作成**

    ```bash
    git checkout -b <branch-type>/<descriptive-name>
    ```

5. **ステージングとコミット**

    ```bash
    git add <files>
    git commit -m "$(cat <<'EOF'
    <type>: <summary>

    <detailed description if needed>

    🤖 Generated with [Claude Code](https://claude.ai/code)

    Co-Authored-By: Claude <noreply@anthropic.com>
    EOF
    )"
    ```

6. **リモートへのプッシュ**

    ```bash
    git push -u origin <branch-name>
    ```

7. **PR の作成**

    ```bash
    gh pr create --title "<タイトル>" --body "$(cat <<'EOF'
    ## 概要
    - <変更点1>
    - <変更点2>

    Fixes #<issue-number>

    ## テストプラン
    - [ ] make check-all が成功することを確認
    - [ ] 関連するテストが追加されていることを確認
    - [ ] ドキュメントが更新されていることを確認

    🤖 Generated with [Claude Code](https://claude.ai/code)
    EOF
    )"
    ```

    **PRタイトルとボディは日本語で記述すること。**

    **重要: Issue リンク**
    - PR本文に `Fixes #<issue-number>` を含めることで、GitHub ProjectsのワークフローがPRとIssueを関連付けます
    - PRマージ時に自動的にIssueが `Done` に移動します（GitHub Projects自動化設定が必要）
    - 詳細は `docs/guidelines/github-projects-automation.md` を参照

8. **GitHub CI のチェック（自動実行）**

    PR作成後、GitHub ActionsのCIステータスを確認し、エラーがあれば修正します：

    ```bash
    # PR番号を取得
    PR_NUMBER=$(gh pr view --json number -q .number)

    # CIステータスをチェック（最大5分待機）
    gh pr checks "$PR_NUMBER" --watch

    # チェック結果を取得
    FAILED_CHECKS=$(gh pr checks "$PR_NUMBER" --json name,conclusion -q '.[] | select(.conclusion=="failure") | .name')
    ```

    **CIエラーがある場合：**

    1. エラー内容を詳細に確認
        ```bash
        # 失敗したチェックのログを取得
        gh run view --log-failed
        ```
    2. エラー原因を特定（format/lint/typecheck/testのいずれか）
    3. 必要な修正を実施
        - format エラー: `make format` を実行
        - lint エラー: `make lint` を実行
        - typecheck エラー: 型エラーを修正
        - test エラー: テストを修正
    4. 修正をコミット＆プッシュ
        ```bash
        git add .
        git commit -m "fix: CI エラーを修正"
        git push
        ```
    5. CI再実行を待機し、すべてのチェックがパスするまで繰り返し

    **CIエラーがない場合：**

    - すべてのチェックがパスしたことを確認
    - PR URLを表示して完了

9. **PRレビューファイルのコミット（オプション）**

    `/review-pr` コマンドで生成されたレビューファイル（`docs/pr-review/pr-review-*.yaml`）がある場合は、追加コミットとしてプッシュします：

    ```bash
    # レビューファイルの確認
    git status docs/pr-review/pr-review-*.yaml 2>/dev/null

    # ファイルがあればコミット
    git add docs/pr-review/pr-review-*.yaml
    git commit -m "$(cat <<'EOF'
    docs: add PR review report

    🤖 Generated with [Claude Code](https://claude.ai/code)

    Co-Authored-By: Claude <noreply@anthropic.com>
    EOF
    )"
    git push
    ```

## 注意事項

1. **コミット前の確認**

    - **code-simplifier** でコード簡素化
    - **quality-checker（--quick モード）** で品質確認
    - 不要なファイルが含まれていないことを確認
    - センシティブな情報が含まれていないことを確認

2. **コミットメッセージ**

    - 変更内容を明確に記述
    - なぜ変更したかを説明（what より why）
    - 日本語での記述も可

3. **PR 作成時**
    - テストプランを必ず含める
    - レビュアーが理解しやすい説明を心がける
    - 関連する Issue があればリンクする

4. **CI チェック**
    - PR作成後は必ずCIの結果を確認
    - エラーがある場合は即座に修正
    - すべてのチェックがパスしてから完了

## 使用例

```bash
# 機能追加のPR
make pr TITLE="feat: ユーザー認証機能を追加" BODY="JWTトークンベースの認証システムを実装しました" LABEL="enhancement"

# バグ修正のPR
make pr TITLE="fix: ログイン時の500エラーを修正" BODY="認証トークンの検証ロジックを修正しました" LABEL="bug"

# ドキュメント更新のPR
make pr TITLE="docs: APIドキュメントを更新" BODY="新しいエンドポイントの説明を追加しました" LABEL="documentation"
```

このコマンドにより、規約に従った一貫性のあるコミットと PR 作成が可能になります。
