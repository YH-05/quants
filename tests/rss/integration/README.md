# RSS Integration Tests

RSS パッケージの統合テストスイート。

## テスト概要

### test_feed_workflow.py

RSS フィードの基本的なワークフローをテストします。

- **フィード登録から取得・検索までのフルフロー**
- **複数フィード登録と検索**
- **Atom フィード処理**
- **並列フィード取得**
- **ファイルロック競合**
- **差分検出による重複排除**

### test_github_project_e2e.py

RSS 収集から GitHub Project 投稿までの E2E フローをテストします。

- **RSS 取得 → フィルタリング → GitHub Issue 作成の完全フロー**
- **重複チェックで既存 Issue をスキップ**
- **GitHub CLI 失敗時のエラーハンドリング**
- **RSS 取得失敗時のリトライロジック**
- **フィルタリングロジック（キーワードマッチング、除外判定）**

## テスト環境のセットアップ

### 前提条件

1. **Python 環境**
   ```bash
   python --version  # 3.12 以上
   ```

2. **依存パッケージのインストール**
   ```bash
   uv sync --all-extras
   ```

3. **フィルター設定ファイルの配置**
   ```bash
   # data/config/finance-news-filter.json が存在することを確認
   ls -la data/config/finance-news-filter.json
   ```

### テストの実行

#### 全統合テストの実行

```bash
# 統合テストマーカー付きテストのみ実行
pytest tests/rss/integration/ -m integration -v
```

#### 特定のテストファイルの実行

```bash
# RSS フィードワークフローテスト
pytest tests/rss/integration/test_feed_workflow.py -v

# GitHub Project E2E テスト
pytest tests/rss/integration/test_github_project_e2e.py -v
```

#### 特定のテストケースの実行

```bash
# 完全フローテストのみ
pytest tests/rss/integration/test_github_project_e2e.py::TestRSSToGitHubE2E::test_正常系_RSS取得からGitHub投稿までの完全フロー -v

# リトライロジックテストのみ
pytest tests/rss/integration/test_github_project_e2e.py::TestRSSToGitHubE2E::test_異常系_RSS取得失敗時のリトライ -v
```

#### カバレッジ付きテスト実行

```bash
pytest tests/rss/integration/ -m integration --cov=rss --cov-report=html -v
```

### テストで使用されるモック

#### 1. HTTPServer (pytest-httpserver)

モック RSS フィードサーバーを提供します。

```python
httpserver.expect_request("/finance.xml").respond_with_data(
    feed_content, content_type="application/rss+xml"
)
```

#### 2. subprocess.run (unittest.mock)

GitHub CLI (`gh` コマンド) の呼び出しをモックします。

```python
@patch("subprocess.run")
def test_example(mock_subprocess):
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = b"https://github.com/user/repo/issues/1"
```

### テストデータ

#### RSS フィードのサンプル

テスト用の RSS フィードは以下のヘルパー関数で生成されます。

```python
from tests.rss.integration.test_github_project_e2e import create_finance_feed

items = [
    {
        "title": "日銀、政策金利を引き上げ",
        "link": "https://example.com/news/boj-rate-hike",
        "pub_date": "Mon, 15 Jan 2024 09:00:00 GMT",
        "description": "日本銀行が政策金利を0.1%引き上げることを決定した",
    },
]

feed_content = create_finance_feed(items)
```

#### フィルター設定

`data/config/finance-news-filter.json` からロードされます。

```python
from tests.rss.integration.test_github_project_e2e import load_filter_config

config = load_filter_config(Path("data/config/finance-news-filter.json"))
```

## トラブルシューティング

### 問題: テストが失敗する

#### 原因 1: フィルター設定ファイルが見つからない

```bash
FileNotFoundError: [Errno 2] No such file or directory: 'data/config/finance-news-filter.json'
```

**解決方法**:
```bash
# ファイルが存在するか確認
ls -la data/config/finance-news-filter.json

# 存在しない場合は作成（サンプルをコピー）
cp data/config/finance-news-filter.json.sample data/config/finance-news-filter.json
```

#### 原因 2: pytest-httpserver がインストールされていない

```bash
ModuleNotFoundError: No module named 'pytest_httpserver'
```

**解決方法**:
```bash
uv sync --all-extras
```

#### 原因 3: テンポラリディレクトリの権限エラー

```bash
PermissionError: [Errno 13] Permission denied: '/tmp/...'
```

**解決方法**:
```bash
# クリーンアップしてから再実行
pytest tests/rss/integration/ --cache-clear -v
```

### 問題: 統合テストが遅い

統合テストは HTTP サーバーや非同期処理を含むため、単体テストより遅くなります。

**対策**:
- 並列実行: `pytest -n auto`（pytest-xdist が必要）
- 特定のテストのみ実行: `-k "test_name"`
- マーカーでフィルタリング: `-m "not slow"`

### 問題: モックが正しく動作しない

#### 原因: subprocess.run のパッチ場所が間違っている

**解決方法**:
```python
# ❌ 間違い: subprocess モジュール自体をパッチ
@patch("subprocess.run")

# ✅ 正解: テスト対象モジュール内の subprocess.run をパッチ
# ただし、このテストでは直接 subprocess.run を呼んでいるので
# テスト関数内でパッチすれば OK
```

## CI/CD での実行

### GitHub Actions

統合テストは `.github/workflows/test.yml` で自動実行されます。

```yaml
- name: Run integration tests
  run: |
    pytest tests/rss/integration/ -m integration --cov=rss --cov-report=xml -v
```

### ローカルでの CI 環境再現

```bash
# GitHub Actions と同じ環境でテスト
act push
```

## テストカバレッジの目標

| カテゴリ | 目標カバレッジ | 現状 |
|---------|--------------|------|
| 統合テスト全体 | 80% 以上 | - |
| E2E フロー | 90% 以上 | - |
| エラーハンドリング | 100% | - |

## 参考資料

- **RSS パッケージドキュメント**: `src/rss/README.md`
- **テスト戦略**: `docs/testing-strategy.md`
- **プロジェクト計画書**: `docs/project/financial-news-rss-collector.md`
- **フィルタリング基準**: `docs/finance-news-filtering-criteria.md`

## 関連 Issue

- [#154](https://github.com/YH-05/quants/issues/154) - ユニットテスト作成（フィルタリングロジック・データ変換処理）
- [#155](https://github.com/YH-05/quants/issues/155) - 統合テスト作成（RSS 収集→GitHub 投稿の E2E）
- [#156](https://github.com/YH-05/quants/issues/156) - プロパティテスト作成（RSS フィードデータのバリデーション）

## 更新履歴

- **2026-01-15**: 初版作成。E2E テスト（test_github_project_e2e.py）を追加。
