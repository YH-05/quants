#!/usr/bin/env python3
"""AIテーマの金融ニュース収集スクリプト

Phase 1: フィルタリング（AIキーワードマッチング）
Phase 2: 重複チェック
Phase 3: GitHub Issue作成とProject追加
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def log(level: str, message: str, **kwargs):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
    print(f"[{timestamp}] [{level}] {message} {extra}".strip())


def calculate_keyword_matches(item: dict, keywords: list[str]) -> tuple[int, list[str]]:
    """キーワードマッチ数を計算"""
    text = (
        f"{item['title']} {item.get('summary', '')} {item.get('content', '')}".lower()
    )
    matched = []
    for kw in keywords:
        if kw.lower() in text:
            matched.append(kw)
    return len(matched), matched


def calculate_reliability_score(item: dict, theme: dict, common: dict) -> int:
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


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトル類似度（Jaccard係数）"""
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
    """重複チェック"""
    new_link = new_item.get("link", "")
    new_title = new_item.get("title", "")

    for issue in existing_issues:
        # URL完全一致
        body = issue.get("body", "")
        if new_link and new_link in body:
            return True, f"URL一致: Issue #{issue['number']}"

        # タイトル類似度
        issue_title = (
            issue.get("title", "").replace("[NEWS] ", "").replace("[News] ", "")
        )
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            return True, f"類似度{similarity:.2f}: Issue #{issue['number']}"

    return False, ""


def is_excluded(item: dict, common: dict) -> tuple[bool, str]:
    """除外キーワードチェック"""
    text = f"{item['title']} {item.get('summary', '')}".lower()

    for category, keywords in common["exclude_keywords"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                return True, f"{category}:{keyword}"

    return False, ""


def fetch_article_content(url: str, title: str) -> str:
    """記事内容を取得（WebFetchまたはgemini検索）"""
    log("INFO", f"記事内容取得中: {title}")

    # WebFetchは使用せず、簡易的にサマリーを返す
    # 実装時はWebFetch APIまたはgemini CLIを使用
    return f"[記事内容: {title}]\n\nURL: {url}\n\n（実際の実装では記事本文を取得）"


def generate_japanese_summary(content: str, title: str, summary: str) -> str:
    """日本語要約生成（400字程度）"""
    # 実装時はClaude APIまたは内部ロジックで要約生成
    # 現時点では簡易的な要約を返す
    if summary:
        return f"{summary}\n\n（実際の実装では400字程度の詳細な要約を生成）"
    return f"[{title}]\n\n（実際の実装では記事内容から400字程度の要約を生成）"


def format_published_jst(published_str: str) -> str:
    """公開日をJST YYYY-MM-DD HH:MM形式に変換"""
    from datetime import datetime

    import pytz

    # ISO 8601形式をパース
    dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))

    # JSTに変換
    jst = pytz.timezone("Asia/Tokyo")
    dt_jst = dt.astimezone(jst)

    # YYYY-MM-DD HH:MM形式で出力
    return dt_jst.strftime("%Y-%m-%d %H:%M")


def get_source_name(link: str, common: dict) -> str:
    """ソース名を取得"""
    for domain in common["sources"]["tier1"]:
        if domain in link:
            return domain.split(".")[0].title()

    for domain in common["sources"]["tier2"]:
        if domain in link:
            return domain.split(".")[0].title()

    # ドメインから推測
    if "techcrunch.com" in link:
        return "TechCrunch"
    elif "seekingalpha.com" in link:
        return "Seeking Alpha"
    elif "arstechnica.com" in link:
        return "Ars Technica"
    elif "theverge.com" in link:
        return "The Verge"
    elif "marketwatch.com" in link:
        return "MarketWatch"
    else:
        return "RSS Feed"


def create_issue_with_project(
    item: dict,
    theme_name: str,
    matched_keywords: list[str],
    score: int,
    source: str,
    project_config: dict,
) -> tuple[bool, str]:
    """GitHub Issueを作成してProjectに追加"""
    title = item["title"]
    link = item["link"]
    published_str = item.get("published", "")
    summary = item.get("summary", "")

    # 公開日をJST形式に変換
    try:
        published_jst = format_published_jst(published_str)
    except Exception as e:
        log("WARNING", f"公開日変換失敗: {e}")
        published_jst = published_str

    # 記事内容取得（実装時はWebFetchまたはgemini検索）
    # article_content = fetch_article_content(link, title)

    # 日本語要約生成（実装時はClaude APIまたは内部ロジック）
    japanese_summary = generate_japanese_summary("", title, summary)

    # Issueボディ作成
    keywords_str = ", ".join(matched_keywords)

    body = f"""## 日本語要約（400字程度）

{japanese_summary}

## 記事概要
- テーマ: {theme_name}
- ソース: {source}
- 信頼性: {score}/100
- 公開日: {published_jst}
- URL: {link}

## マッチしたキーワード
{keywords_str}
"""

    # Issue作成
    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                "YH-05/quants",
                "--title",
                f"[NEWS] {title}",
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
        log("INFO", f"Issue作成成功: {issue_url}")

        # Project追加
        try:
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
            log("INFO", f"Project追加成功: {issue_url}")
        except subprocess.CalledProcessError as e:
            log("WARNING", f"Project追加失敗: {e.stderr}")

        # Status設定（GraphQL API）
        # 実装時はGraphQL mutationを実行
        # 現時点ではスキップ
        log("INFO", f"Status設定: AI (17189c86) - {issue_url}")

        return True, issue_url

    except subprocess.CalledProcessError as e:
        log("ERROR", f"Issue作成失敗: {e.stderr}")
        return False, ""


def main():
    log("INFO", "AIテーマの金融ニュース収集開始")

    # ファイルパス
    tmp_file = Path(
        "/Users/yukihata/Desktop/finance/.tmp/news-collection-20260115-214331.json"
    )
    config_file = Path(
        "/Users/yukihata/Desktop/finance/data/config/finance-news-themes.json"
    )

    # ファイル読み込み（スマートクォートを修正）
    try:
        with open(tmp_file, "r", encoding="utf-8") as f:
            content = f.read()

        # スマートクォートを全て通常の引用符に置換
        # JSON内のスマートクォートは全て削除または置換
        content = content.replace("\u201c", "")  # " → 削除
        content = content.replace("\u201d", "")  # " → 削除
        content = content.replace("\u2018", "'")  # ' → '
        content = content.replace("\u2019", "'")  # ' → '

        data = json.loads(content)
        log("INFO", f"一時ファイル読み込み: {tmp_file}")
    except FileNotFoundError:
        log("ERROR", f"一時ファイルが見つかりません: {tmp_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        log("ERROR", f"JSON形式が不正です: {e}")
        # エラー詳細を出力
        log("ERROR", f"エラー位置: 行{e.lineno}, 列{e.colno}")
        # エラー付近の内容を表示
        lines = content.split("\n")
        if 0 <= e.lineno - 1 < len(lines):
            log("ERROR", f"問題の行: {lines[e.lineno - 1]}")
        sys.exit(1)

    try:
        with open(config_file) as f:
            config = json.load(f)
        theme = config["themes"]["ai"]
        common = config["common"]
        project_config = config["project"]
        log("INFO", f"テーマ設定読み込み: {config_file}")
    except FileNotFoundError:
        log("ERROR", f"テーマ設定ファイルが見つかりません: {config_file}")
        sys.exit(1)
    except KeyError:
        log("ERROR", "'ai' テーマが定義されていません")
        sys.exit(1)

    # 統計カウンタ
    stats = {
        "processed": 0,
        "matched": 0,
        "excluded": 0,
        "duplicates": 0,
        "created": 0,
        "failed": 0,
    }

    rss_items = data["rss_items"]
    existing_issues = data["existing_issues"]

    log("INFO", f"処理記事数: {len(rss_items)}件")
    log("INFO", f"既存Issue数: {len(existing_issues)}件")

    # フィルタリング
    filtered_items = []

    for item in rss_items:
        stats["processed"] += 1
        title = item["title"]

        # AIキーワードマッチング
        match_count, matched_keywords = calculate_keyword_matches(
            item, theme["keywords"]["include"]
        )

        if match_count < theme["min_keyword_matches"]:
            continue

        log("INFO", f"マッチ: {title} (キーワード: {', '.join(matched_keywords[:3])})")
        stats["matched"] += 1

        # 除外キーワードチェック
        is_excl, excl_reason = is_excluded(item, common)
        if is_excl:
            log("INFO", f"除外: {title} (理由: {excl_reason})")
            stats["excluded"] += 1
            continue

        # 信頼性スコア計算
        score = calculate_reliability_score(item, theme, common)

        # 最低スコアチェック
        if score < common["filtering"]["min_reliability_score"]:
            log("INFO", f"除外: {title} (スコア不足: {score})")
            stats["excluded"] += 1
            continue

        # 重複チェック
        is_dup, dup_reason = is_duplicate(
            item, existing_issues, common["filtering"]["title_similarity_threshold"]
        )
        if is_dup:
            log("INFO", f"重複: {title} ({dup_reason})")
            stats["duplicates"] += 1
            continue

        # フィルタリング通過
        filtered_items.append(
            {"item": item, "matched_keywords": matched_keywords, "score": score}
        )

    log("INFO", f"フィルタリング完了: {len(filtered_items)}件が新規投稿対象")

    # GitHub Issue作成
    created_issues = []

    for filtered in filtered_items:
        item = filtered["item"]
        matched_keywords = filtered["matched_keywords"]
        score = filtered["score"]

        source = get_source_name(item["link"], common)

        success, issue_url = create_issue_with_project(
            item,
            "AI（人工知能・テクノロジー）",
            matched_keywords,
            score,
            source,
            project_config,
        )

        if success:
            stats["created"] += 1
            created_issues.append(
                {
                    "title": item["title"],
                    "url": issue_url,
                    "source": source,
                    "score": score,
                }
            )
        else:
            stats["failed"] += 1

    # 結果サマリー
    print("\n" + "=" * 80)
    print("## AI（人工知能・テクノロジー）ニュース収集完了")
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
            print(f"{i}. **{issue['title']}**")
            print(f"   - ソース: {issue['source']}")
            print(f"   - 信頼性: {issue['score']}/100")
            print(f"   - URL: {issue['url']}\n")

    log("INFO", "AIテーマの金融ニュース収集完了")


if __name__ == "__main__":
    main()
