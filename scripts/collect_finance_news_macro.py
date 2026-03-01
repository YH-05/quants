#!/usr/bin/env python3
"""Macro Economics（マクロ経済）ニュース収集スクリプト"""

import json
import subprocess
import sys
from pathlib import Path


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）"""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def matches_macro_keywords(item: dict, theme: dict) -> tuple[bool, list[str]]:
    """マクロ経済テーマのキーワードにマッチするかチェック"""
    # 検索対象テキスト
    text = (
        f"{item['title']} {item.get('summary', '')} {item.get('content', '')}".lower()
    )

    # キーワードマッチング
    matched_keywords = []
    for keyword in theme["keywords"]["include"]:
        if keyword.lower() in text:
            matched_keywords.append(keyword)

    # 最低マッチ数チェック
    min_matches = theme["min_keyword_matches"]
    is_match = len(matched_keywords) >= min_matches

    return is_match, matched_keywords


def is_excluded(item: dict, common: dict, theme: dict) -> bool:
    """除外対象かチェック"""
    text = f"{item['title']} {item.get('summary', '')}".lower()

    # 除外キーワードチェック
    for category, keywords in common["exclude_keywords"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                # マクロ経済キーワードも含む場合は除外しない
                is_match, _ = matches_macro_keywords(item, theme)
                if not is_match:
                    print(
                        f"  除外: {item['title'][:60]}... (理由: {category}:{keyword})"
                    )
                    return True

    return False


def calculate_reliability_score(item: dict, theme: dict, common: dict) -> int:
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


def is_duplicate(new_item: dict, existing_issues: list[dict], threshold: float) -> bool:
    """既存Issueと重複しているかチェック"""
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        # URL完全一致
        body = issue.get("body", "")
        if new_link and new_link in body:
            print(f"  重複（URL一致）: {new_title[:60]}... → Issue #{issue['number']}")
            return True

        # タイトル類似度チェック
        issue_title = issue.get("title", "").replace("[NEWS] ", "")
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            print(
                f"  重複（類似度{similarity:.2f}）: {new_title[:60]}... → Issue #{issue['number']}"
            )
            return True

    return False


def fetch_article_content(url: str, title: str) -> str:
    """記事内容を取得（WebFetchまたはgemini検索）"""
    print(f"    記事内容取得中: {url}")

    # gemini CLI経由でWeb検索
    try:
        domain = url.split("/")[2] if "/" in url else url
        query = f"{title} {domain}"

        result = subprocess.run(
            ["gemini", "--prompt", f"WebSearch: {query}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0 and result.stdout:
            return result.stdout
        else:
            return f"記事URL: {url}\n\n記事内容の取得に失敗しました。"
    except Exception as e:
        print(f"    警告: 記事内容取得失敗: {e}")
        return f"記事URL: {url}\n\n記事内容の取得に失敗しました。"


def generate_japanese_summary(content: str, title: str, max_length: int = 400) -> str:
    """記事内容から日本語要約を生成"""
    print("    日本語要約生成中...")

    prompt = f"""以下の記事内容を、日本語で400字程度に要約してください。

要約のポイント:
- 主要な事実と数値データを優先
- 背景や影響を簡潔に説明
- 投資判断に有用な情報を強調
- 箇条書きではなく、文章形式で

記事タイトル: {title}

記事内容:
{content[:2000]}
"""

    try:
        result = subprocess.run(
            ["claude", "--no-stream", "--prompt", prompt],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        else:
            return "（要約生成失敗）"
    except Exception as e:
        print(f"    警告: 要約生成失敗: {e}")
        return "（要約生成失敗）"


def format_published_jst(published_str: str) -> str:
    """公開日をJST YYYY-MM-DD HH:MM形式に変換"""
    try:
        from datetime import datetime, timedelta, timezone

        # ISO 8601形式をパース（標準ライブラリのみ）
        # "2026-01-15T00:00:00+00:00" 形式
        if "+" in published_str or published_str.endswith("Z"):
            dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(published_str)

        # JSTに変換（UTC+9）
        jst = timezone(timedelta(hours=9))
        dt_jst = dt.astimezone(jst)

        # YYYY-MM-DD HH:MM形式で出力
        return dt_jst.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"    警告: 日付変換失敗: {e}")
        return published_str


def create_issue(
    item: dict,
    japanese_summary: str,
    published_jst: str,
    matched_keywords: list[str],
    score: int,
    source: str,
) -> str | None:
    """GitHub Issueを作成"""
    title = f"[NEWS] {item['title']}"

    # マッチキーワードをMarkdownリスト形式に
    keywords_md = "\n".join(f"- {kw}" for kw in matched_keywords)

    body = f"""## 日本語要約（400字程度）

{japanese_summary}

## 記事概要
- テーマ: Macro Economics（マクロ経済）
- ソース: {source}
- 信頼性: {score}/100
- 公開日: {published_jst}
- URL: {item["link"]}

## マッチしたキーワード
{keywords_md}
"""

    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                "YH-05/finance",
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
        print(f"  ✓ Issue作成成功: {issue_url}")
        return issue_url

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Issue作成失敗: {item['title'][:60]}...")
        print(f"    エラー: {e.stderr}")
        return None


def add_to_project(issue_url: str) -> str | None:
    """Project 15に追加"""
    try:
        result = subprocess.run(
            ["gh", "project", "item-add", "15", "--owner", "YH-05", "--url", issue_url],
            capture_output=True,
            text=True,
            check=True,
        )

        # Project Item IDを抽出
        output = json.loads(result.stdout)
        item_id = output["id"]
        print(f"  ✓ Project追加成功: Item ID {item_id}")
        return item_id

    except subprocess.CalledProcessError as e:
        print("  ✗ Project追加失敗")
        print(f"    エラー: {e.stderr}")
        return None


def set_status_macro(
    issue_url: str, project_item_id: str, project_config: dict
) -> bool:
    """StatusをMacro Economicsに設定"""
    try:
        # Issue番号を抽出
        issue_number = int(issue_url.split("/")[-1])

        # Step 1: Issue Node IDを取得
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
        target_item_id = None
        for item in project_items:
            if item["project"]["number"] == 15:
                target_item_id = item["id"]
                break

        if not target_item_id:
            print("  ✗ Status設定失敗: Project Item IDが見つかりません")
            return False

        # Step 3: StatusフィールドをMacro Economicsに設定
        mutation = f"""
mutation {{
  updateProjectV2ItemFieldValue(
    input: {{
      projectId: "{project_config["project_id"]}"
      itemId: "{target_item_id}"
      fieldId: "{project_config["status_field_id"]}"
      value: {{
        singleSelectOptionId: "c40731f6"
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

        print("  ✓ Status設定成功: Macro Economics")
        return True

    except subprocess.CalledProcessError as e:
        print("  ✗ Status設定失敗")
        print(f"    エラー: {e.stderr}")
        return False
    except Exception as e:
        print(f"  ✗ Status設定失敗: {e}")
        return False


def main():
    """メイン処理"""
    print("=" * 80)
    print("Macro Economics（マクロ経済）ニュース収集")
    print("=" * 80)
    print()

    # Phase 1: 初期化
    print("[Phase 1] 初期化")
    print("-" * 80)

    # 一時ファイル読み込み（パース済みデータ）
    tmp_file = Path("/Users/yukihata/Desktop/finance/.tmp/news-collection-parsed.json")
    if not tmp_file.exists():
        print(f"エラー: 一時ファイルが見つかりません: {tmp_file}")
        print("parse_broken_json.pyを先に実行してください")
        sys.exit(1)

    print(f"一時ファイル読み込み: {tmp_file}")
    with open(tmp_file) as f:
        data = json.load(f)

    # 既存Issueを取得（GitHub CLIから直接）
    print("既存Issue読み込み中...")
    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                "YH-05/finance",
                "--limit",
                "1000",
                "--label",
                "news",
                "--json",
                "number,title,body,url",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data["existing_issues"] = json.loads(result.stdout)
        print(f"✓ 既存Issue読み込み: {len(data['existing_issues'])}件")
    except subprocess.CalledProcessError as e:
        print(f"警告: 既存Issue取得失敗: {e.stderr}")
        data["existing_issues"] = []

    rss_items = data["rss_items"]
    existing_issues = data["existing_issues"]
    print(f"  RSS記事: {len(rss_items)}件")
    print(f"  既存Issue: {len(existing_issues)}件")
    print()

    # テーマ設定読み込み
    config_file = Path(
        "/Users/yukihata/Desktop/finance/data/config/finance-news-themes.json"
    )
    print(f"テーマ設定読み込み: {config_file}")
    with open(config_file) as f:
        config = json.load(f)

    theme = config["themes"]["macro"]
    common = config["common"]
    project_config = config["project"]
    print("  テーマ: Macro Economics")
    print(f"  GitHub Status ID: {theme['github_status_id']}")
    print()

    # 統計カウンタ初期化
    stats = {
        "processed": 0,
        "matched": 0,
        "excluded": 0,
        "duplicates": 0,
        "created": 0,
        "failed": 0,
    }
    created_issues = []

    # Phase 2: フィルタリング
    print("[Phase 2] フィルタリング")
    print("-" * 80)

    filtered_items = []

    for item in rss_items:
        stats["processed"] += 1

        # キーワードマッチング
        is_match, matched_keywords = matches_macro_keywords(item, theme)
        if not is_match:
            continue

        stats["matched"] += 1
        print(f"✓ マッチ: {item['title'][:60]}...")
        print(f"  キーワード: {', '.join(matched_keywords[:5])}")

        # 除外チェック
        if is_excluded(item, common, theme):
            stats["excluded"] += 1
            continue

        # 重複チェック
        if is_duplicate(
            item, existing_issues, common["filtering"]["title_similarity_threshold"]
        ):
            stats["duplicates"] += 1
            continue

        # スコア計算
        score = calculate_reliability_score(item, theme, common)

        # 最低スコアチェック
        if score < common["filtering"]["min_reliability_score"]:
            print(f"  除外（低スコア）: スコア={score}")
            stats["excluded"] += 1
            continue

        # ソース抽出
        link = item.get("link", "")
        source = "不明"
        for domain in common["sources"]["tier1"]:
            if domain in link:
                source = domain
                break
        if source == "不明":
            for domain in common["sources"]["tier2"]:
                if domain in link:
                    source = domain
                    break

        filtered_items.append(
            {
                "item": item,
                "matched_keywords": matched_keywords,
                "score": score,
                "source": source,
            }
        )
        print(f"  → フィルタリング通過（スコア: {score}/100）")
        print()

    print(f"フィルタリング結果: {len(filtered_items)}件")
    print()

    # Phase 3: GitHub投稿
    print("[Phase 3] GitHub投稿")
    print("-" * 80)

    for filtered in filtered_items:
        item = filtered["item"]
        matched_keywords = filtered["matched_keywords"]
        score = filtered["score"]
        source = filtered["source"]

        print(f"処理中: {item['title'][:60]}...")

        # 記事内容取得（スキップ - 手動で要約）
        # article_content = fetch_article_content(item['link'], item['title'])

        # 日本語要約生成（簡易版 - RSSサマリーを使用）
        japanese_summary = item.get("summary", "（要約なし）") or "（要約なし）"
        if len(japanese_summary) > 400:
            japanese_summary = japanese_summary[:400] + "..."

        # 公開日変換
        published_jst = format_published_jst(item.get("published", ""))

        # Issue作成
        issue_url = create_issue(
            item, japanese_summary, published_jst, matched_keywords, score, source
        )

        if not issue_url:
            stats["failed"] += 1
            print()
            continue

        # Project追加
        project_item_id = add_to_project(issue_url)

        if not project_item_id:
            stats["failed"] += 1
            print()
            continue

        # Status設定
        if set_status_macro(issue_url, project_item_id, project_config):
            stats["created"] += 1
            created_issues.append(
                {
                    "url": issue_url,
                    "title": item["title"],
                    "score": score,
                    "source": source,
                }
            )
        else:
            stats["failed"] += 1

        print()

    # Phase 4: 結果報告
    print()
    print("=" * 80)
    print("Macro Economics（マクロ経済）ニュース収集完了")
    print("=" * 80)
    print()

    print("### 処理統計")
    print(f"- **処理記事数**: {stats['processed']}件")
    print(f"- **テーママッチ**: {stats['matched']}件")
    print(f"- **除外**: {stats['excluded']}件")
    print(f"- **重複**: {stats['duplicates']}件")
    print(f"- **新規投稿**: {stats['created']}件")
    print(f"- **投稿失敗**: {stats['failed']}件")
    print()

    if created_issues:
        print("### 投稿されたニュース")
        print()
        for i, issue in enumerate(created_issues, 1):
            issue_num = issue["url"].split("/")[-1]
            print(f"{i}. **{issue['title'][:60]}...** [#{issue_num}]")
            print(f"   - ソース: {issue['source']}")
            print(f"   - 信頼性: {issue['score']}/100")
            print(f"   - URL: {issue['url']}")
            print()


if __name__ == "__main__":
    main()
