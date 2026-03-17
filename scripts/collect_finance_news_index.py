#!/usr/bin/env python3
"""Index（株価指数）テーマのニュース収集エージェント

一時ファイルから記事を読み込み、Indexテーマに関連するニュースを
フィルタリングしてGitHub Project 15に投稿する。
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def log_info(msg: str) -> None:
    """情報ログを出力"""
    print(f"[INFO] {msg}")


def log_error(msg: str) -> None:
    """エラーログを出力"""
    print(f"[ERROR] {msg}", file=sys.stderr)


def log_warning(msg: str) -> None:
    """警告ログを出力"""
    print(f"[WARNING] {msg}", file=sys.stderr)


def load_json_file(filepath: Path) -> dict:
    """JSONファイルを読み込む"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

            # JSON内の不正な引用符を修正
            import re

            # パターン1: "summary": ""text""  → "summary": "\"text\""
            # パターン2: "field": ""text.", → "field": "\"text.\"",
            # より汎用的な修正: フィールド値内の先頭・末尾の二重引用符をエスケープ
            def fix_quotes(match):
                field = match.group(1)
                value = match.group(2)
                # 値の先頭と末尾の引用符をエスケープ
                if value.startswith('"') and value.endswith('"'):
                    value = '\\"' + value[1:-1] + '\\"'
                return f'"{field}": "{value}"'

            # "field": "value" パターンで value に引用符が含まれる場合を修正
            # より安全なアプローチ: ""で始まって""で終わるパターンのみ修正
            content = re.sub(
                r'"(summary|title|body)":\s*""([^"]*)""', r'"\1": "\\\"\2\\\""', content
            )

            return json.loads(content, strict=False)
    except FileNotFoundError:
        log_error(f"ファイルが見つかりません: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log_error(f"JSON形式が不正です: {e}")
        log_error(
            "JSONファイルを手動で修正するか、オーケストレーターを再実行してください"
        )

        # デバッグ用: エラー箇所の前後を表示
        try:
            lines = content.split("\n")
            error_line = int(str(e).split("line")[1].split()[0])
            log_error(f"エラー箇所（行 {error_line} 付近）:")
            for i in range(max(0, error_line - 3), min(len(lines), error_line + 3)):
                log_error(f"  {i + 1}: {lines[i][:100]}")
        except Exception:  # nosec B110
            pass

        sys.exit(1)


def matches_index_keywords(item: dict, theme: dict) -> tuple[bool, list[str]]:
    """Indexテーマのキーワードにマッチするかチェック"""
    text = f"{item.get('title', '')} {item.get('summary', '')} {item.get('content', '')}".lower()

    matched_keywords = []
    for keyword in theme["keywords"]["include"]:
        if keyword.lower() in text:
            matched_keywords.append(keyword)

    min_matches = theme["min_keyword_matches"]
    is_match = len(matched_keywords) >= min_matches

    return is_match, matched_keywords


def is_excluded(item: dict, common: dict) -> tuple[bool, str]:
    """除外対象かチェック"""
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()

    for category, keywords in common["exclude_keywords"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                return True, f"{category}:{keyword}"

    return False, ""


def calculate_reliability_score(
    item: dict, theme: dict, common: dict, keyword_matches: int
) -> int:
    """信頼性スコアを計算（0-100）"""
    link = item.get("link", "")

    # Tier判定
    tier = 1
    for domain in common["sources"]["tier1"]:
        if domain in link:
            tier = 3
            break
    if tier == 1:
        for domain in common["sources"]["tier2"]:
            if domain in link:
                tier = 2
                break

    # キーワードマッチ度
    keyword_ratio = min(keyword_matches / 10, 1.0)

    # Priority boost
    boost = 1.0
    title_lower = item.get("title", "").lower()
    for priority_kw in theme["keywords"]["priority_boost"]:
        if priority_kw.lower() in title_lower:
            boost = 1.5
            break

    # Reliability weight
    weight = theme.get("reliability_weight", 1.0)

    # スコア計算
    score = tier * keyword_ratio * boost * weight * 100

    return min(int(score), 100)


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）"""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def is_duplicate(
    new_item: dict, existing_issues: list[dict], threshold: float
) -> tuple[bool, str]:
    """既存Issueと重複しているかチェック"""
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        # URL完全一致
        body = issue.get("body", "")
        if new_link and new_link in body:
            return True, f"URL一致: Issue #{issue['number']}"

        # タイトル類似度チェック
        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            return True, f"類似度{similarity:.2f}: Issue #{issue['number']}"

    return False, ""


def fetch_article_content(url: str, title: str) -> str:
    """記事内容を取得（gemini検索を使用）"""
    try:
        # gemini CLIで記事タイトルとドメインで検索
        domain = url.split("/")[2] if url else "finance news"
        query = f"{title} {domain}"

        log_info(f"記事内容取得: {title}")
        result = subprocess.run(
            ["gemini", "--prompt", f"WebSearch: {query}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            log_warning(f"記事内容取得失敗: {title}")
            return f"記事タイトル: {title}\nURL: {url}\n（詳細な内容は取得できませんでした）"

    except Exception as e:
        log_warning(f"記事内容取得エラー: {e}")
        return (
            f"記事タイトル: {title}\nURL: {url}\n（詳細な内容は取得できませんでした）"
        )


def generate_japanese_summary(content: str, max_length: int = 400) -> str:
    """記事内容から日本語要約を生成（400字程度）"""
    # 簡易要約（実際はClaude APIなどを使用）
    # ここでは最初の400文字を抽出
    lines = content.split("\n")
    summary_parts = []
    total_length = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if total_length + len(line) > max_length:
            break
        summary_parts.append(line)
        total_length += len(line)

    summary = "\n".join(summary_parts)
    if total_length > max_length:
        summary = summary[:max_length] + "..."

    return summary if summary else "（要約を生成できませんでした）"


def format_published_jst(published_str: str) -> str:
    """公開日をJST YYYY-MM-DD HH:MM形式に変換"""
    try:
        # ISO 8601形式をパース
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        # JSTに変換（UTC+9時間）
        from datetime import timedelta, timezone

        jst = timezone(timedelta(hours=9))
        dt_jst = dt.astimezone(jst)
        return dt_jst.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        log_warning(f"日時変換エラー: {e}")
        return published_str


def create_issue(
    item: dict,
    japanese_summary: str,
    published_jst: str,
    matched_keywords: list[str],
    score: int,
    project_config: dict,
) -> tuple[bool, str]:
    """GitHub Issueを作成してProject 15に追加"""

    title = f"[NEWS] {item.get('title', 'Untitled')}"
    source = item.get("feed_title", "Unknown")
    link = item.get("link", "")
    keywords_str = ", ".join(matched_keywords[:5])  # 最初の5個のみ

    body = f"""## 日本語要約（400字程度）

{japanese_summary}

## 記事概要
- テーマ: Index（株価指数）
- ソース: {source}
- 信頼性: {score}/100
- 公開日: {published_jst}
- URL: {link}

## マッチしたキーワード
{keywords_str}
"""

    try:
        # Issue作成
        log_info(f"Issue作成: {item.get('title', 'Untitled')}")
        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                "YH-05/quants",
                "--title",
                title,
                "--body",
                body,
                "--label",
                "news",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Issue URLを取得
        issue_url = result.stdout.strip()
        if not issue_url:
            log_error("Issue URLが取得できませんでした")
            return False, ""

        log_info(f"Issue作成成功: {issue_url}")

        # Issue番号を抽出
        issue_number = issue_url.split("/")[-1]

        # Project 15に追加
        log_info(f"Project追加: Issue #{issue_number}")
        subprocess.run(
            [
                "gh",
                "project",
                "item-add",
                str(project_config["number"]),
                "--owner",
                project_config["owner"],
                "--url",
                issue_url,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        log_info(f"Project追加成功: Issue #{issue_number}")

        # Status設定（GraphQL API）
        set_status_to_index(issue_number, project_config)

        return True, issue_url

    except subprocess.CalledProcessError as e:
        log_error(f"Issue作成失敗: {e.stderr}")
        return False, ""


def set_status_to_index(issue_number: str, project_config: dict) -> None:
    """StatusをIndexに設定"""
    try:
        # Step 1: Issue Node IDを取得
        query1 = f"""
        query {{
          repository(owner: "{project_config["owner"]}", name: "finance") {{
            issue(number: {issue_number}) {{
              id
            }}
          }}
        }}
        """

        result1 = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query1}"],
            capture_output=True,
            text=True,
            check=True,
        )

        data1 = json.loads(result1.stdout)
        issue_node_id = data1["data"]["repository"]["issue"]["id"]

        # Step 2: Project Item IDを取得
        query2 = f"""
        query {{
          node(id: "{issue_node_id}") {{
            ... on Issue {{
              projectItems(first: 10) {{
                nodes {{
                  id
                  project {{
                    number
                  }}
                }}
              }}
            }}
          }}
        }}
        """

        result2 = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query2}"],
            capture_output=True,
            text=True,
            check=True,
        )

        data2 = json.loads(result2.stdout)
        project_items = data2["data"]["node"]["projectItems"]["nodes"]

        # Project 15のItem IDを探す
        project_item_id = None
        for item in project_items:
            if item["project"]["number"] == project_config["number"]:
                project_item_id = item["id"]
                break

        if not project_item_id:
            log_warning(f"Project Item IDが見つかりません: Issue #{issue_number}")
            return

        # Step 3: StatusをIndexに設定
        mutation = f"""
        mutation {{
          updateProjectV2ItemFieldValue(
            input: {{
              projectId: "{project_config["project_id"]}"
              itemId: "{project_item_id}"
              fieldId: "{project_config["status_field_id"]}"
              value: {{
                singleSelectOptionId: "f75ad846"
              }}
            }}
          ) {{
            projectV2Item {{
              id
            }}
          }}
        }}
        """

        subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            capture_output=True,
            text=True,
            check=True,
        )

        log_info(f"Status設定成功: Issue #{issue_number} → Index")

    except Exception as e:
        log_warning(f"Status設定失敗: Issue #{issue_number}: {e}")


def main():
    """メイン処理"""
    log_info("=== Index（株価指数）ニュース収集開始 ===")

    # ファイルパス設定
    repo_root = Path(__file__).parent.parent
    tmp_file = repo_root / ".tmp" / "news-collection-20260115-214331.json"
    theme_file = repo_root / "data" / "config" / "finance-news-themes.json"

    # データ読み込み
    log_info(f"一時ファイル読み込み: {tmp_file}")
    data = load_json_file(tmp_file)

    log_info(f"テーマ設定読み込み: {theme_file}")
    config = load_json_file(theme_file)

    theme = config["themes"]["index"]
    common = config["common"]
    project_config = config["project"]

    rss_items = data.get("rss_items", [])
    existing_issues = data.get("existing_issues", [])

    log_info(f"RSS記事数: {len(rss_items)}")
    log_info(f"既存Issue数: {len(existing_issues)}")

    # 統計カウンタ
    stats = {
        "processed": 0,
        "matched": 0,
        "excluded": 0,
        "duplicates": 0,
        "created": 0,
        "failed": 0,
    }

    created_issues = []

    # フィルタリング処理
    log_info("フィルタリング開始...")

    for item in rss_items:
        stats["processed"] += 1

        # テーマキーワードマッチング
        is_match, matched_keywords = matches_index_keywords(item, theme)

        if not is_match:
            continue

        stats["matched"] += 1
        log_info(
            f"マッチ: {item.get('title', 'Untitled')} (キーワード: {', '.join(matched_keywords[:3])})"
        )

        # 除外キーワードチェック
        excluded, reason = is_excluded(item, common)
        if excluded:
            stats["excluded"] += 1
            log_info(f"除外: {item.get('title', 'Untitled')} (理由: {reason})")
            continue

        # 重複チェック
        is_dup, dup_reason = is_duplicate(
            item, existing_issues, common["filtering"]["title_similarity_threshold"]
        )
        if is_dup:
            stats["duplicates"] += 1
            log_info(f"重複: {item.get('title', 'Untitled')} ({dup_reason})")
            continue

        # 信頼性スコア計算
        score = calculate_reliability_score(item, theme, common, len(matched_keywords))

        # 最低スコアチェック
        if score < common["filtering"]["min_reliability_score"]:
            log_info(f"スコア不足: {item.get('title', 'Untitled')} (スコア: {score})")
            continue

        # 記事内容取得と要約生成
        article_content = fetch_article_content(
            item.get("link", ""), item.get("title", "")
        )
        japanese_summary = generate_japanese_summary(article_content)
        published_jst = format_published_jst(item.get("published", ""))

        # Issue作成
        success, issue_url = create_issue(
            item,
            japanese_summary,
            published_jst,
            matched_keywords,
            score,
            project_config,
        )

        if success:
            stats["created"] += 1
            issue_number = issue_url.split("/")[-1]
            created_issues.append(
                {
                    "number": issue_number,
                    "title": item.get("title", "Untitled"),
                    "url": issue_url,
                    "source": item.get("feed_title", "Unknown"),
                    "score": score,
                }
            )
        else:
            stats["failed"] += 1

    # 結果サマリー出力
    print("\n" + "=" * 80)
    print("## Index（株価指数）ニュース収集完了")
    print("=" * 80)
    print("\n### 処理統計")
    print(f"- **処理記事数**: {stats['processed']}件")
    print(f"- **テーママッチ**: {stats['matched']}件")
    print(f"- **除外**: {stats['excluded']}件")
    print(f"- **重複**: {stats['duplicates']}件")
    print(f"- **新規投稿**: {stats['created']}件")
    print(f"- **投稿失敗**: {stats['failed']}件")

    if created_issues:
        print("\n### 投稿されたニュース\n")
        for i, issue in enumerate(created_issues, 1):
            print(f"{i}. **{issue['title']}** [#{issue['number']}]")
            print(f"   - ソース: {issue['source']}")
            print(f"   - 信頼性: {issue['score']}/100")
            print(f"   - URL: {issue['url']}\n")

    log_info("処理完了")


if __name__ == "__main__":
    main()
