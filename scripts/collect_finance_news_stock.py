#!/usr/bin/env python3
"""Stock（個別銘柄）テーマのニュース収集スクリプト

オーケストレーターが準備した一時ファイルから、個別銘柄関連のニュースを
フィルタリングし、GitHub Project 15に投稿する。
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def log(message: str) -> None:
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）"""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def matches_stock_keywords(
    item: dict[str, Any], theme: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Stockテーマのキーワードにマッチするかチェック"""
    text = (
        f"{item['title']} {item.get('summary', '')} {item.get('content', '')}".lower()
    )

    matched_keywords = []
    for keyword in theme["keywords"]["include"]:
        if keyword.lower() in text:
            matched_keywords.append(keyword)

    min_matches = theme["min_keyword_matches"]
    is_match = len(matched_keywords) >= min_matches

    return is_match, matched_keywords


def is_excluded(
    item: dict[str, Any], common: dict[str, Any], theme: dict[str, Any]
) -> bool:
    """除外対象かチェック"""
    text = f"{item['title']} {item.get('summary', '')}".lower()

    for category, keywords in common["exclude_keywords"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                # 金融キーワードも含む場合は除外しない
                is_match, _ = matches_stock_keywords(item, theme)
                if not is_match:
                    log(f"除外: {item['title'][:50]}... (理由: {category}:{keyword})")
                    return True

    return False


def calculate_reliability_score(
    item: dict[str, Any], theme: dict[str, Any], common: dict[str, Any]
) -> int:
    """信頼性スコアを計算"""
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
    text = (
        f"{item['title']} {item.get('summary', '')} {item.get('content', '')}".lower()
    )
    keyword_matches = sum(
        1 for kw in theme["keywords"]["include"] if kw.lower() in text
    )
    keyword_ratio = min(keyword_matches / 10, 1.0)

    # Priority boost
    boost = 1.0
    for priority_kw in theme["keywords"]["priority_boost"]:
        if priority_kw.lower() in item["title"].lower():
            boost = 1.5
            break

    # Reliability weight
    weight = theme.get("reliability_weight", 1.0)

    # スコア計算
    score = tier * keyword_ratio * boost * weight * 100

    return min(int(score), 100)


def is_duplicate(
    new_item: dict[str, Any], existing_issues: list[dict[str, Any]], threshold: float
) -> bool:
    """既存Issueと重複しているかチェック"""
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        # URL完全一致
        body = issue.get("body", "")
        if new_link and new_link in body:
            log(f"重複（URL一致）: {new_title[:50]}... (Issue #{issue['number']})")
            return True

        # タイトル類似度チェック
        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            log(
                f"重複（類似度{similarity:.2f}）: {new_title[:50]}... (Issue #{issue['number']})"
            )
            return True

    return False


def fetch_article_content(url: str, title: str) -> str:
    """記事内容を取得（WebFetch失敗時はgemini検索で代替）"""
    log(f"記事内容取得中: {title[:50]}...")

    # gemini CLI経由でWeb検索（WebFetchの代替）
    domain = url.split("/")[2] if "/" in url else ""
    query = f"{title} {domain}"

    try:
        result = subprocess.run(
            [
                "gemini",
                "--prompt",
                f"この記事の内容を日本語で400字程度に要約してください。重要なポイント、数値データ、背景、影響を含めてください。記事タイトル: {title}",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            log("警告: gemini検索失敗。RSSサマリーを使用します")
            return ""
    except Exception as e:
        log(f"警告: 記事内容取得エラー: {e}")
        return ""


def format_published_jst(published_str: str) -> str:
    """公開日をJST YYYY-MM-DD HH:MM形式に変換"""
    try:
        from datetime import datetime

        import pytz

        # ISO 8601形式をパース
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        # JSTに変換
        jst = pytz.timezone("Asia/Tokyo")
        dt_jst = dt.astimezone(jst)

        # YYYY-MM-DD HH:MM形式で出力
        return dt_jst.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        log(f"警告: 公開日変換エラー: {e}")
        return published_str


def create_issue(
    item: dict[str, Any],
    matched_keywords: list[str],
    score: int,
    japanese_summary: str,
    published_jst: str,
) -> str | None:
    """GitHub Issueを作成し、URLを返す"""
    title = f"[NEWS] {item['title']}"
    source = (
        item.get("link", "").split("/")[2] if "/" in item.get("link", "") else "Unknown"
    )

    # 日本語要約がない場合はRSSサマリーを使用
    summary_section = f"""## 日本語要約（400字程度）

{japanese_summary if japanese_summary else item.get("summary", "（要約なし）")}
"""

    body = f"""{summary_section}

## 記事概要
- テーマ: Stock（個別銘柄）
- ソース: {source}
- 信頼性: {score}/100
- 公開日: {published_jst}
- URL: {item["link"]}

## マッチしたキーワード
{", ".join(matched_keywords)}
"""

    try:
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

        # Issue URLを抽出
        issue_url = result.stdout.strip()
        return issue_url

    except subprocess.CalledProcessError as e:
        log(f"エラー: Issue作成失敗: {e.stderr}")
        return None


def add_to_project(issue_url: str) -> str | None:
    """Project 15に追加し、Project Item IDを返す"""
    try:
        result = subprocess.run(
            ["gh", "project", "item-add", "15", "--owner", "YH-05", "--url", issue_url],
            capture_output=True,
            text=True,
            check=True,
        )

        # Project Item IDを抽出
        output = json.loads(result.stdout)
        return output["id"]

    except subprocess.CalledProcessError as e:
        log(f"エラー: Project追加失敗: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        log(f"エラー: Project追加のレスポンス解析失敗: {e}")
        return None


def set_status(
    issue_url: str, project_id: str, status_field_id: str, status_id: str
) -> bool:
    """StatusフィールドをStockに設定"""
    # Step 1: Issue Node IDを取得
    issue_number = issue_url.split("/")[-1]

    try:
        query1 = f"""
query {{
  repository(owner: "YH-05", name: "finance") {{
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

    except Exception as e:
        log(f"エラー: Issue Node ID取得失敗: {e}")
        return False

    # Step 2: Project Item IDを取得
    try:
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
            if item["project"]["number"] == 15:
                project_item_id = item["id"]
                break

        if not project_item_id:
            log("エラー: Project Item IDが見つかりません")
            return False

    except Exception as e:
        log(f"エラー: Project Item ID取得失敗: {e}")
        return False

    # Step 3: Statusを設定
    try:
        mutation = f"""
mutation {{
  updateProjectV2ItemFieldValue(
    input: {{
      projectId: "{project_id}"
      itemId: "{project_item_id}"
      fieldId: "{status_field_id}"
      value: {{
        singleSelectOptionId: "{status_id}"
      }}
    }}
  ) {{
    projectV2Item {{
      id
    }}
  }}
}}
"""
        result3 = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={mutation}"],
            capture_output=True,
            text=True,
            check=True,
        )

        log(f"Status設定成功: Issue #{issue_number} → Stock")
        return True

    except Exception as e:
        log(f"警告: Status設定失敗: {e}")
        log("Issue作成は成功しています。手動でStatusを設定してください。")
        return False


def main() -> None:
    """メイン処理"""
    log("=== Stock（個別銘柄）ニュース収集開始 ===")

    # Phase 1: 初期化
    log("[Phase 1] 初期化")

    # 一時ファイルを探す（最新のものを使用）
    tmp_dir = Path("/Users/yukihata/Desktop/finance/.tmp")
    tmp_files = list(tmp_dir.glob("news-collection-*.json"))

    if not tmp_files:
        log("エラー: 一時ファイルが見つかりません")
        log("オーケストレーターが正しく実行されたか確認してください")
        sys.exit(1)

    tmp_file = max(tmp_files, key=lambda p: p.stat().st_mtime)
    log(f"一時ファイル読み込み: {tmp_file.name}")

    try:
        with open(tmp_file, "r", encoding="utf-8") as f:
            content = f.read()

        # JSON構文エラーを修正（エスケープされていないクォートなど）
        import re

        # summary/content フィールド内のエスケープされていないクォートを修正
        def fix_field_quotes(match):
            field_name = match.group(1)
            field_value = match.group(2)
            # ダブルクォートをエスケープ（既にエスケープされているものは除く）
            fixed_value = re.sub(r'(?<!\\)"', r"\"", field_value)
            return f'"{field_name}": "{fixed_value}"'

        # より安全なアプローチ: jsonデコードエラーの場合のみ修正を試みる
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            log(
                f"警告: JSON構文エラー検出。自動修正を試みます... (line {e.lineno}, col {e.colno})"
            )

            # 問題のある行を特定して修正
            lines = content.split("\n")
            if e.lineno <= len(lines):
                problem_line = lines[e.lineno - 1]
                log(f"問題の行: {problem_line[:100]}")

            # 簡易的な修正: summaryフィールドの不正なクォートを除去
            content = re.sub(
                r'"summary": "([^"]*)"([^"]*)"([^"]*)"', r'"summary": "\1\2\3"', content
            )

            # 再度パース
            try:
                data = json.loads(content)
                log("JSON修正成功")
            except json.JSONDecodeError as e2:
                log(f"エラー: JSON修正失敗: {e2}")
                sys.exit(1)
    except FileNotFoundError:
        log(f"エラー: ファイルが見つかりません: {tmp_file}")
        sys.exit(1)

    # テーマ設定読み込み
    config_file = Path(
        "/Users/yukihata/Desktop/finance/data/config/finance-news-themes.json"
    )
    try:
        with open(config_file) as f:
            config = json.load(f)
        theme = config["themes"]["stock"]
        common = config["common"]
        project = config["project"]
    except FileNotFoundError:
        log("エラー: テーマ設定ファイルが見つかりません")
        sys.exit(1)
    except KeyError:
        log("エラー: 'stock' テーマが定義されていません")
        sys.exit(1)

    # 統計カウンタ初期化
    processed = 0
    matched = 0
    excluded = 0
    duplicates = 0
    created = 0
    failed = 0

    # RSS記事と既存Issueを取得
    rss_items = data.get("rss_items", [])
    existing_issues = data.get("existing_issues", [])

    log(f"処理記事数: {len(rss_items)}件")
    log(f"既存Issue数: {len(existing_issues)}件")

    # Phase 2: フィルタリング
    log("[Phase 2] フィルタリング")

    filtered_items: list[tuple[dict[str, Any], list[str], int]] = []

    for item in rss_items:
        processed += 1

        # テーママッチング
        is_match, matched_keywords = matches_stock_keywords(item, theme)
        if not is_match:
            continue

        matched += 1
        log(
            f"マッチ: {item['title'][:50]}... (キーワード: {', '.join(matched_keywords[:3])})"
        )

        # 除外チェック
        if is_excluded(item, common, theme):
            excluded += 1
            continue

        # 信頼性スコア計算
        score = calculate_reliability_score(item, theme, common)

        # 最低スコアチェック
        if score < common["filtering"]["min_reliability_score"]:
            log(f"除外（信頼性スコア不足）: {item['title'][:50]}... (スコア: {score})")
            excluded += 1
            continue

        # 重複チェック
        if is_duplicate(
            item, existing_issues, common["filtering"]["title_similarity_threshold"]
        ):
            duplicates += 1
            continue

        filtered_items.append((item, matched_keywords, score))

    log(f"フィルタリング完了: {len(filtered_items)}件が新規記事")

    # Phase 3: GitHub投稿
    log("[Phase 3] GitHub Issue作成")

    created_issues: list[dict[str, Any]] = []

    for item, matched_keywords, score in filtered_items:
        # 記事内容取得と要約生成
        japanese_summary = fetch_article_content(item["link"], item["title"])

        # 公開日をJST形式に変換
        published_jst = format_published_jst(item.get("published", ""))

        # Issue作成
        issue_url = create_issue(
            item, matched_keywords, score, japanese_summary, published_jst
        )

        if not issue_url:
            failed += 1
            continue

        issue_number = issue_url.split("/")[-1]
        log(f"Issue作成成功: #{issue_number} - {item['title'][:50]}...")

        # Project追加
        project_item_id = add_to_project(issue_url)
        if project_item_id:
            log(f"Project追加成功: #{issue_number}")
        else:
            log(f"警告: Project追加失敗: #{issue_number}")

        # Status設定
        set_status(
            issue_url,
            project["project_id"],
            project["status_field_id"],
            theme["github_status_id"],
        )

        created += 1
        created_issues.append(
            {
                "number": issue_number,
                "title": item["title"],
                "url": issue_url,
                "source": item.get("link", "").split("/")[2]
                if "/" in item.get("link", "")
                else "Unknown",
                "score": score,
            }
        )

    # Phase 4: 結果報告
    log("[Phase 4] 結果報告")

    print("\n" + "=" * 80)
    print("## Stock（個別銘柄）ニュース収集完了")
    print("=" * 80)
    print("\n### 処理統計")
    print(f"- **処理記事数**: {processed}件")
    print(f"- **テーママッチ**: {matched}件")
    print(f"- **除外**: {excluded}件")
    print(f"- **重複**: {duplicates}件")
    print(f"- **新規投稿**: {created}件")
    print(f"- **投稿失敗**: {failed}件")

    if created_issues:
        print("\n### 投稿されたニュース\n")
        for i, issue in enumerate(created_issues, 1):
            print(f"{i}. **{issue['title']}** [#{issue['number']}]")
            print(f"   - ソース: {issue['source']}")
            print(f"   - 信頼性: {issue['score']}/100")
            print(f"   - URL: {issue['url']}\n")

    print("=" * 80)


if __name__ == "__main__":
    main()
