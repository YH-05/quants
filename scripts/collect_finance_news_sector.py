#!/usr/bin/env python3
"""Sectorテーマの金融ニュース収集スクリプト."""

import json
import subprocess
import sys
from pathlib import Path


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（Jaccard係数）."""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


def matches_sector_keywords(item: dict, theme: dict) -> tuple[bool, list[str]]:
    """Sectorテーマのキーワードにマッチするかチェック."""
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


def is_excluded(item: dict, common: dict) -> bool:
    """除外対象かチェック."""
    text = f"{item['title']} {item.get('summary', '')}".lower()

    for category, keywords in common["exclude_keywords"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                print(f"  [除外] {item['title']} (理由: {category}:{keyword})")
                return True

    return False


def calculate_reliability_score(item: dict, theme: dict, common: dict) -> int:
    """信頼性スコアを計算."""
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
    """既存Issueと重複しているかチェック."""
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        body = issue.get("body", "")
        if new_link and new_link in body:
            print(f"  [重複] {new_title} (URL一致: Issue #{issue['number']})")
            return True

        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            print(
                f"  [重複] {new_title} (類似度{similarity:.2f}: Issue #{issue['number']})"
            )
            return True

    return False


def fetch_article_content(url: str, title: str) -> str:
    """記事内容を取得（WebFetch代替としてgemini検索）."""
    try:
        # gemini CLI経由でWeb検索
        domain = url.split("/")[2] if "/" in url else ""
        query = f"{title} {domain}"

        result = subprocess.run(
            [
                "gemini",
                "--prompt",
                f"WebSearch: {query}. この記事の内容を詳しく要約してください。",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  [警告] gemini検索失敗: {title}")
            return f"記事タイトル: {title}\n\n※記事内容の取得に失敗しました。"

    except Exception as e:
        print(f"  [警告] 記事内容取得エラー: {e}")
        return f"記事タイトル: {title}\n\n※記事内容の取得に失敗しました。"


def format_published_jst(published_str: str) -> str:
    """公開日をJST YYYY-MM-DD HH:MM形式に変換."""
    try:
        from datetime import datetime

        import pytz

        # ISO 8601形式をパース
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

        # JSTに変換
        jst = pytz.timezone("Asia/Tokyo")
        dt_jst = dt.astimezone(jst)

        return dt_jst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return published_str


def create_issue(
    item: dict, matched_keywords: list[str], score: int, article_content: str
) -> str | None:
    """GitHub Issueを作成してURLを返す."""
    title = f"[NEWS] {item['title']}"
    source = (
        item.get("link", "").split("/")[2] if "/" in item.get("link", "") else "Unknown"
    )
    published_jst = format_published_jst(item.get("published", ""))

    # 日本語要約を生成（簡易版：article_contentから最初の400文字）
    japanese_summary = (
        article_content[:400] if len(article_content) > 400 else article_content
    )

    body = f"""## 日本語要約（400字程度）

{japanese_summary}

## 記事概要
- テーマ: Sector（セクター分析）
- ソース: {source}
- 信頼性: {score}/100
- 公開日: {published_jst}
- URL: {item.get("link", "")}

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
        print(f"  [エラー] Issue作成失敗: {item['title']}")
        print(f"  詳細: {e.stderr}")
        return None


def add_to_project(issue_url: str) -> str | None:
    """Project 15に追加してProject Item IDを返す."""
    try:
        result = subprocess.run(
            ["gh", "project", "item-add", "15", "--owner", "YH-05", "--url", issue_url],
            capture_output=True,
            text=True,
            check=True,
        )

        # Project Item IDを抽出
        output = json.loads(result.stdout)
        return output.get("id")

    except Exception as e:
        print(f"  [警告] Project追加失敗: {issue_url}")
        print(f"  詳細: {e}")
        return None


def set_status(issue_url: str, project_item_id: str) -> bool:
    """StatusをSectorに設定."""
    # Issue番号を抽出
    issue_number = issue_url.split("/")[-1]

    try:
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
        project_item_id = None
        for item in project_items:
            if item["project"]["number"] == 15:
                project_item_id = item["id"]
                break

        if not project_item_id:
            print(f"  [警告] Project Item ID取得失敗: Issue #{issue_number}")
            return False

        # Step 3: StatusフィールドをSectorに設定
        mutation = f"""
        mutation {{
          updateProjectV2ItemFieldValue(
            input: {{
              projectId: "PVT_kwHOBoK6AM4BMpw_"
              itemId: "{project_item_id}"
              fieldId: "PVTSSF_lAHOBoK6AM4BMpw_zg739ZE"
              value: {{
                singleSelectOptionId: "98236657"
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

        print(f"  [成功] Status設定: Issue #{issue_number} → Sector")
        return True

    except Exception as e:
        print(f"  [警告] Status設定失敗: Issue #{issue_number}")
        print(f"  詳細: {e}")
        return False


def main():
    """メイン処理."""
    # Phase 1: 初期化
    print("[INFO] Sectorテーマ処理開始\n")

    # 一時ファイル読み込み
    tmp_file = Path(
        "/Users/yukihata/Desktop/finance/.tmp/news-collection-20260115-214331.json"
    )
    if not tmp_file.exists():
        print(f"[エラー] 一時ファイルが見つかりません: {tmp_file}")
        sys.exit(1)

    try:
        with open(tmp_file, encoding="utf-8") as f:
            content = f.read()

            # JSONの修正処理
            import re

            # 1. 不正なエスケープ `\\"` を削除（値が引用符で始まる/終わる場合）
            #    "summary": "\\"One...\\"" → "summary": "One..."
            content = re.sub(r'(:\s*)"\\\\(")', r'\1"', content)  # 開始
            content = re.sub(r'(\\\\")(")', r"\1", content)  # 終了

            # 2. 余分なバックスラッシュを削除
            content = re.sub(r'\\\\(["\'])', r"\\\1", content)

            # 3. スマートクォートを通常のクォートに置換
            content = content.replace("\u201c", '"').replace("\u201d", '"')
            content = content.replace("\u2018", "'").replace("\u2019", "'")

            data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[エラー] JSON形式エラー: {e}")
        print(f"[情報] 詳細: {e!s}")

        # デバッグ情報出力
        error_line = (
            int(str(e).split("line ")[1].split()[0]) if "line " in str(e) else 0
        )
        if error_line > 0:
            lines = content.split("\n")
            if error_line - 1 < len(lines):
                print(
                    f"[デバッグ] 問題の行 {error_line}: {lines[error_line - 1][:200]}"
                )

        sys.exit(1)

    # テーマ設定読み込み
    config_file = Path(
        "/Users/yukihata/Desktop/finance/data/config/finance-news-themes.json"
    )
    with open(config_file) as f:
        config = json.load(f)

    theme = config["themes"]["sector"]
    common = config["common"]

    # 統計カウンタ初期化
    processed = 0
    matched = 0
    excluded = 0
    duplicates = 0
    created = 0
    failed = 0

    created_issues = []

    # Phase 2: フィルタリング
    print("[INFO] テーママッチング中...")

    for item in data["rss_items"]:
        processed += 1

        # 除外キーワードチェック
        if is_excluded(item, common):
            excluded += 1
            continue

        # テーマキーワードマッチング
        is_match, matched_keywords = matches_sector_keywords(item, theme)
        if not is_match:
            continue

        matched += 1
        print(f"  [マッチ] {item['title']} (キーワード: {', '.join(matched_keywords)})")

        # 重複チェック
        threshold = common["filtering"]["title_similarity_threshold"]
        if is_duplicate(item, data["existing_issues"], threshold):
            duplicates += 1
            continue

        # 信頼性スコア計算
        score = calculate_reliability_score(item, theme, common)

        # Phase 3: GitHub投稿
        print(f"  [投稿中] {item['title']} (スコア: {score})")

        # 記事内容取得（簡易版：スキップ）
        article_content = f"記事タイトル: {item['title']}\n\n{item.get('summary', '')}"

        # Issue作成
        issue_url = create_issue(item, matched_keywords, score, article_content)
        if not issue_url:
            failed += 1
            continue

        issue_number = issue_url.split("/")[-1]
        print(f"  [成功] Issue作成: #{issue_number}")

        # Project追加
        project_item_id = add_to_project(issue_url)
        if project_item_id:
            print(f"  [成功] Project追加: #{issue_number}")

            # Status設定
            set_status(issue_url, project_item_id)

        created += 1
        created_issues.append(
            {
                "number": issue_number,
                "title": item["title"],
                "url": issue_url,
                "score": score,
            }
        )

    # Phase 4: 結果報告
    print("\n" + "=" * 80)
    print("## Sector（セクター分析）ニュース収集完了\n")
    print("### 処理統計")
    print(f"- **処理記事数**: {processed}件")
    print(f"- **テーママッチ**: {matched}件")
    print(f"- **除外**: {excluded}件")
    print(f"- **重複**: {duplicates}件")
    print(f"- **新規投稿**: {created}件")
    print(f"- **投稿失敗**: {failed}件\n")

    if created_issues:
        print("### 投稿されたニュース\n")
        for i, issue in enumerate(created_issues, 1):
            source = "（ソース不明）"
            print(f"{i}. **{issue['title']}** [#{issue['number']}]")
            print(f"   - 信頼性: {issue['score']}/100")
            print(f"   - URL: {issue['url']}\n")


if __name__ == "__main__":
    main()
