---
name: finance-news-workflow
description: 金融ニュース収集の簡素化ワークフロー。Python CLI前処理→RSS要約ベースIssue一括作成→結果報告。全テーマ5分以内完了。
allowed-tools: Read, Bash, Task
---

# 金融ニュース収集ワークフロー

RSSフィードから金融ニュースを自動収集し、GitHub Project #15に投稿するワークフロースキル。

## 処理時間目標

| 指標 | 目標 | 根拠 |
|------|------|------|
| 全テーマ合計 | 5分以内 | Issue #1855 受け入れ条件 |
| Phase 1（Python前処理） | 30秒以内 | 決定論的処理のみ、ネットワークI/Oなし |
| Phase 2（Issue一括作成） | 4分以内 | 11テーマ並列、各テーマ最大10件 |
| Phase 3（結果報告） | 30秒以内 | 集約・表示のみ |

## アーキテクチャ

```
/finance-news-workflow (このスキル = オーケストレーター)
  │
  ├── Phase 1: Python CLI前処理（30秒以内）
  │     └── prepare_news_session.py
  │           ├── 既存Issue取得・URL抽出
  │           ├── RSS取得（全テーマ一括、ローカルデータから）
  │           ├── 公開日時フィルタリング
  │           ├── 重複チェック
  │           ├── 上位N件選択（--top-n、デフォルト10件/テーマ）
  │           └── テーマ別JSONファイル出力（.tmp/news-batches/）
  │
  ├── Phase 2: news-article-fetcher 並列呼び出し（4分以内）
  │     ├── RSS要約ベースでIssue作成（本文取得スキップ）
  │     ├── 11テーマを1メッセージで並列呼び出し
  │     └── 各テーマ最大10件（Phase 1で制限済み）
  │
  └── Phase 3: 結果集約・報告（30秒以内）
        └── 各エージェントの完了を待ち、統計を報告
```

### 旧アーキテクチャとの比較

| 項目 | 旧フロー（6段階） | 新フロー（3段階） |
|------|-------------------|-------------------|
| 処理段階数 | 6段階 | 3段階 |
| テーマ判定 | AI判定（遅い） | フィード割当で代替（不要） |
| コンテンツ取得 | 3-tier フォールバック（遅い） | RSS要約を直接使用（高速） |
| 処理時間 | 10-30分 | 5分以内 |
| Issue品質 | 本文ベース要約 | RSS要約ベース（needs-review付き） |
| 記事数/テーマ | 最大20件 | 最大10件（--top-n） |

### 簡素化の根拠

1. **テーマ判定の廃止**: `finance-news-themes.json` でフィードがテーマ別に割当済み。AI判定は冗長
2. **コンテンツ取得の遅延**: 本文取得（trafilatura/Playwright）は1記事5-30秒。RSS要約で先にIssue作成し、本文検証は後から実行可能
3. **上位N件制限**: 各テーマ最新10件に制限することで処理量を大幅削減

## 使用方法

```bash
# 標準実行（デフォルト: 過去7日間、各テーマ最新10件）
/finance-news-workflow

# オプション付き
/finance-news-workflow --days 3 --themes "index,macro_cnbc" --top-n 5

# 本文検証モード（後から実行、needs-review ラベルの記事を検証）
/finance-news-workflow --verify-content
```

## Phase 1: Python CLI前処理

### ステップ1.1: 環境確認

```bash
# テーマ設定ファイル確認
test -f data/config/finance-news-themes.json

# GitHub CLI 確認
gh auth status
```

### ステップ1.2: Python CLI実行 + テーマ別JSON出力

```bash
# 1. セッションファイル作成（--top-n で各テーマの記事数を制限）
uv run python scripts/prepare_news_session.py --days ${days} --top-n ${top_n}

# 2. テーマ別JSONファイル作成
python3 << 'EOF'
import json
from pathlib import Path

# 最新のセッションファイルを取得
tmp_dir = Path(".tmp")
session_files = sorted(tmp_dir.glob("news-*.json"), reverse=True)
session_file = session_files[0]
session = json.load(open(session_file))

output_dir = Path(".tmp/news-batches")
output_dir.mkdir(exist_ok=True)

config = session["config"]

for theme_key, theme_data in session["themes"].items():
    articles = theme_data["articles"]
    theme_config = theme_data["theme_config"]

    issue_config = {
        "theme_key": theme_key,
        "theme_label": theme_config["name_ja"].split(" (")[0],
        "status_option_id": theme_config["github_status_id"],
        "project_id": config["project_id"],
        "project_number": config["project_number"],
        "project_owner": config["project_owner"],
        "repo": "YH-05/quants",
        "status_field_id": config["status_field_id"],
        "published_date_field_id": config["published_date_field_id"]
    }

    output_file = output_dir / f"{theme_key}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "articles": articles,
            "issue_config": issue_config
        }, f, ensure_ascii=False, indent=2)

    print(f"{theme_key}: {len(articles)} articles -> {output_file}")
EOF
```

**出力ファイル形式**（各テーマ）:

```json
{
  "articles": [
    {
      "url": "https://...",
      "title": "...",
      "summary": "...",
      "feed_source": "...",
      "published": "2026-01-29T12:00:00+00:00"
    }
  ],
  "issue_config": {
    "theme_key": "index",
    "theme_label": "株価指数",
    "status_option_id": "3925acc3",
    "project_id": "PVT_kwHOBoK6AM4BMpw_",
    "project_number": 15,
    "project_owner": "YH-05",
    "repo": "YH-05/quants",
    "status_field_id": "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE",
    "published_date_field_id": "PVTF_lAHOBoK6AM4BMpw_zg8BzrI"
  }
}
```

## Phase 2: news-article-fetcher 並列呼び出し（RSS要約モード）

### ステップ2.1: 全テーマを並列で呼び出し

**重要**: 11テーマ全てを**1つのメッセージ内で並列呼び出し**すること。

```python
# 11テーマを並列で呼び出し（1メッセージに11個のTask呼び出し）
themes = [
    "index", "stock", "sector",
    "macro_cnbc", "macro_other",
    "ai_cnbc", "ai_nasdaq", "ai_tech",
    "finance_cnbc", "finance_nasdaq", "finance_other"
]

# 各テーマのJSONファイルを読み込み、news-article-fetcherに渡す
for theme in themes:
    json_file = f".tmp/news-batches/{theme}.json"
    data = json.load(open(json_file))

    if not data["articles"]:
        # 記事が0件のテーマはスキップ
        continue

    Task(
        subagent_type="news-article-fetcher",
        description=f"{theme}: {len(data['articles'])}件の記事処理",
        prompt=f"""以下の記事データをRSS要約モードで処理してください。

```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

RSS要約モード:
1. 本文取得（trafilatura/Playwright）をスキップ
2. RSS要約をそのまま使用してIssue作成
3. 全Issueに needs-review ラベルを付与
4. Issue作成・close → Project追加 → Status/Date設定

JSON形式で結果を返してください。""",
        run_in_background=True  # バックグラウンド実行
    )
```

### ステップ2.2: 完了待ち

全エージェントの完了を待ち、結果を集約:

```python
# TaskOutputで各エージェントの結果を取得
results = {}
for theme in themes:
    result = TaskOutput(task_id=agent_ids[theme], block=True, timeout=300000)
    results[theme] = parse_result(result)
```

## Phase 3: 結果報告

### サマリー出力形式

```markdown
## 金融ニュース収集完了

### 全体統計

| 項目 | 件数 |
|------|------|
| 前処理：取得記事数 | {total} |
| 前処理：重複スキップ | {duplicates} |
| 投稿対象 | {accessible} |
| Issue作成成功 | {created} |
| Issue作成失敗 | {failed} |

### テーマ別統計

| テーマ | 対象 | 作成 | 失敗 |
|--------|------|------|------|
| Index（株価指数） | {n} | {created} | {failed} |
| Stock（個別銘柄） | {n} | {created} | {failed} |
| ... | ... | ... | ... |

### セッション情報

- **実行時刻**: {timestamp}
- **セッションファイル**: {session_file}
- **処理モード**: RSS要約モード（needs-review付き）
```

## パラメータ一覧

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| --days | 7 | 過去何日分のニュースを対象とするか |
| --themes | all | 対象テーマ（index,stock,... / all） |
| --top-n | 10 | 各テーマの最大記事数（公開日時の新しい順） |
| --verify-content | false | 本文検証モード（needs-review記事を後から検証） |

## テーマ一覧

| テーマキー | 日本語名 | GitHub Status |
|------------|----------|---------------|
| index | 株価指数 | Index |
| stock | 個別銘柄 | Stock |
| sector | セクター | Sector |
| macro_cnbc | マクロ経済 (CNBC) | Macro |
| macro_other | マクロ経済 (その他) | Macro |
| ai_cnbc | AI (CNBC) | AI |
| ai_nasdaq | AI (NASDAQ) | AI |
| ai_tech | AI (テックメディア) | AI |
| finance_cnbc | 金融 (CNBC) | Finance |
| finance_nasdaq | 金融 (NASDAQ) | Finance |
| finance_other | 金融 (その他) | Finance |

## 関連リソース

| リソース | パス |
|---------|------|
| Python CLI前処理 | `scripts/prepare_news_session.py` |
| テーマ設定 | `data/config/finance-news-themes.json` |
| news-article-fetcher | `.claude/agents/news-article-fetcher.md` |
| GitHub Project | https://github.com/users/YH-05/projects/15 |

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| E001: テーマ設定ファイルエラー | ファイル存在・JSON形式を確認 |
| E002: Python CLI エラー | prepare_news_session.py のログを確認 |
| E003: GitHub CLI エラー | `gh auth login` で認証 |
| E004: news-article-fetcher 失敗 | JSONファイルから手動再実行 |

### KG Integration (Optional)

収集完了後、結果をナレッジグラフに投入できます:

```bash
/emit-graph-queue --command finance-news-workflow --input .tmp/news-batches/{theme}_articles.json
/save-to-graph --source finance-news-workflow
```

## 変更履歴

### 2026-02-09: ワークフロー処理の簡素化（Issue #1855）

- **処理フロー簡素化**: 6段階 → 3段階に削減
  - テーマ判定（AI）を廃止（フィード割当で代替）
  - コンテンツ取得（3-tier）を遅延実行に変更
  - RSS要約ベースでIssue作成（高速）
- **処理時間目標設定**: 全テーマ5分以内
- **上位N件制限**: `--top-n` パラメータ追加（デフォルト10件/テーマ）
- **RSS要約モード**: 本文取得をスキップ、needs-reviewラベル付与
- **本文検証モード**: `--verify-content` で後から本文検証可能

### 2026-01-29: テーマエージェント廃止

- **テーマエージェント廃止**: 11個のテーマエージェントを `trash/agents/` に移動
- **直接呼び出し方式**: スキルから news-article-fetcher を直接呼び出す
- **ネスト削減**: 3段 → 1段（スキル → news-article-fetcher）
- **ペイウォールチェック削除**: prepare_news_session.py から削除（処理時間: 30分 → 10秒）

### 2026-01-29: 新アーキテクチャ移行（初版）

- **オーケストレーター廃止**: `finance-news-orchestrator.md` を `trash/` に移動
- **Python CLI前処理追加**: 決定論的処理をPythonに移行
- **3段階フォールバック追加**: trafilatura → Playwright → RSS Summary

## 制約事項

- **GitHub API**: 1時間あたり5000リクエスト
- **RSS取得**: フィードの保持件数に依存（通常10-50件）
- **重複チェック**: Python CLIで事前実行
- **実行頻度**: 1日1回を推奨
- **処理時間**: 全テーマ5分以内（目標）
