#!/usr/bin/env python3
"""
Finance News Collection Script

RSSフィードから金融ニュースを収集し、GitHub Project #15 に投稿する。
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# RSS パッケージをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rss import FeedReader


def load_filter_config(config_path: Path) -> dict[str, Any]:
    """フィルター設定を読み込む"""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"エラー: フィルター設定ファイルが見つかりません: {config_path}")
        print("作成方法: docs/finance-news-filtering-criteria.md を参照")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON形式が不正です: {e}")
        sys.exit(1)


def matches_financial_keywords(
    item: dict[str, Any], filter_config: dict[str, Any]
) -> tuple[bool, list[str]]:
    """金融キーワードにマッチするかチェック"""
    text = f"{item.get('title', '')} {item.get('summary', '')} {item.get('content', '')}".lower()

    include_keywords = filter_config["keywords"]["include"]
    matched_keywords = []

    for category, keywords in include_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text:
                matched_keywords.append(f"{category}:{keyword}")

    min_matches = filter_config["filtering"]["min_keyword_matches"]
    return len(matched_keywords) >= min_matches, matched_keywords


def is_excluded(item: dict[str, Any], filter_config: dict[str, Any]) -> bool:
    """除外対象かチェック"""
    text = f"{item.get('title', '')} {item.get('summary', '')}".lower()

    exclude_keywords = filter_config["keywords"]["exclude"]

    for category, keywords in exclude_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text:
                # 金融キーワードも含む場合は除外しない
                is_financial, _ = matches_financial_keywords(item, filter_config)
                if not is_financial:
                    return True

    return False


def calculate_reliability_score(
    item: dict[str, Any], filter_config: dict[str, Any]
) -> int:
    """信頼性スコアを計算"""
    link = item.get("link", "")
    sources = filter_config["sources"]

    # 情報源のTierを判定
    tier = 1
    for tier_name, domains in sources.items():
        for domain in domains:
            if domain in link:
                if tier_name == "tier1":
                    tier = 3
                elif tier_name == "tier2":
                    tier = 2
                else:
                    tier = 1
                break
        if tier > 1:
            break

    # キーワードマッチ度
    text = f"{item.get('title', '')} {item.get('summary', '')} {item.get('content', '')}".lower()
    keyword_matches = 0

    for category, keywords in filter_config["keywords"]["include"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                keyword_matches += 1

    keyword_match_ratio = min(keyword_matches / 10, 1.0)  # 10キーワードマッチで満点

    # スコア計算
    score = tier * keyword_match_ratio * 100

    return int(score)


def get_existing_news_issues(repo: str) -> list[dict[str, Any]]:
    """既存のニュースIssueを取得"""
    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repo,
                "--label",
                "news",
                "--limit",
                "100",
                "--json",
                "number,title,url,body",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"警告: 既存Issue取得失敗: {e.stderr}")
        return []


def calculate_title_similarity(title1: str, title2: str) -> float:
    """タイトルの類似度を計算（簡易版）"""
    words1 = set(title1.lower().split())
    words2 = set(title2.lower().split())

    if not words1 or not words2:
        return 0.0

    common = words1.intersection(words2)
    total = words1.union(words2)

    return len(common) / len(total)


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
            return True

        # タイトル類似度チェック
        issue_title = issue.get("title", "")
        similarity = calculate_title_similarity(new_title, issue_title)

        if similarity >= threshold:
            return True

    return False


def create_github_issue(
    repo: str,
    item: dict[str, Any],
    reliability_score: int,
    matched_keywords: list[str],
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """GitHub Issueを作成"""
    # タイトル: [News] + 英語タイトル
    title = f"[News] {item.get('title', 'Untitled')}"

    # タイトルの長さ制限（GitHubの制限に対応）
    if len(title) > 200:
        title = title[:197] + "..."

    # Issue Body テンプレート（日本語要約セクション追加）
    body = f"""## 日本語要約（400字程度）

[記事を読んで要約を追加してください]

## 記事概要

**ソース**: {item.get("source", "Unknown")}
**信頼性**: {reliability_score}/100
**公開日**: {item.get("published", "Unknown")}
**URL**: {item.get("link", "No URL")}

## マッチしたキーワード

{", ".join(matched_keywords) if matched_keywords else "なし"}

## 次のアクション

- [ ] 記事を確認
- [ ] 日本語要約を追加（400字程度）
- [ ] 記事作成の必要性を判断
- [ ] 関連する既存記事があれば参照

---

自動収集: /collect-finance-news
"""

    if dry_run:
        print(f"[DRY-RUN] Issue作成: {title}")
        print(f"  URL: {item.get('link')}")
        print(f"  信頼性: {reliability_score}")
        return None

    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "news",
                "--assignee",
                "@me",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        issue_url = result.stdout.strip()

        # Issue番号を抽出
        issue_number = issue_url.split("/")[-1]

        print(f"✓ Issue #{issue_number} 作成: {title[:80]}...")

        return {
            "number": issue_number,
            "title": title,
            "url": issue_url,
        }

    except subprocess.CalledProcessError as e:
        print(f"✗ Issue作成失敗: {e.stderr}")
        return None


def main():
    """メイン処理"""
    print("=" * 80)
    print("金融ニュース収集スクリプト")
    print("=" * 80)
    print()

    # パラメータ
    dry_run = False  # 本番実行
    limit = 50
    repo = "YH-05/quants"
    project_number = 15

    print("設定:")
    print(f"  リポジトリ: {repo}")
    print(f"  プロジェクト: #{project_number}")
    print(f"  最大取得記事数: {limit}")
    print(f"  実行モード: {'DRY-RUN' if dry_run else '本番'}")
    print()

    # Phase 1: 初期化
    print("[Phase 1] 初期化")
    print("-" * 80)

    # フィルター設定読み込み
    config_path = Path("data/config/finance-news-filter.json")
    print(f"フィルター設定: {config_path}")
    filter_config = load_filter_config(config_path)
    print("✓ フィルター設定を読み込みました")
    print()

    # RSS データディレクトリ
    data_dir = Path("data/raw/rss")
    print(f"RSS データディレクトリ: {data_dir}")

    if not data_dir.exists():
        print(f"エラー: RSS データディレクトリが存在しません: {data_dir}")
        sys.exit(1)

    print("✓ RSS データディレクトリを確認しました")
    print()

    # Phase 2: ニュース収集・フィルタリング
    print("[Phase 2] ニュース収集・フィルタリング")
    print("-" * 80)

    # RSSリーダーを作成
    reader = FeedReader(data_dir)

    # 全エントリー取得
    print(f"記事を取得中... (limit={limit})")
    items = reader.get_items(feed_id=None, limit=limit, offset=0)

    print(f"✓ 取得記事数: {len(items)}件")
    print()

    # フィルタリング処理
    print("フィルタリング中...")

    filtered_items = []
    excluded_count = 0

    for item in items:
        # 辞書形式に変換
        item_dict = {
            "title": item.title,
            "link": item.link,
            "summary": item.summary or "",
            "content": item.content or "",
            "published": item.published,
            "source": "RSS Feed",  # FeedItemにはsource属性がないため固定値
        }

        # 金融キーワードマッチング
        is_financial, matched_keywords = matches_financial_keywords(
            item_dict, filter_config
        )

        if not is_financial:
            excluded_count += 1
            continue

        # 除外判定
        if is_excluded(item_dict, filter_config):
            excluded_count += 1
            continue

        # 信頼性スコアリング
        reliability_score = calculate_reliability_score(item_dict, filter_config)

        # 最低信頼性スコアチェック
        min_score = filter_config["filtering"]["min_reliability_score"]
        if reliability_score < min_score:
            excluded_count += 1
            continue

        filtered_items.append(
            {
                "item": item_dict,
                "reliability_score": reliability_score,
                "matched_keywords": matched_keywords,
            }
        )

    print(f"✓ 金融キーワードマッチ: {len(filtered_items)}件")
    print(f"✓ 除外: {excluded_count}件")
    print()

    # 重複チェック
    print("重複チェック中...")

    existing_issues = get_existing_news_issues(repo)
    print(f"✓ 既存ニュースIssue: {len(existing_issues)}件")

    threshold = filter_config["filtering"]["title_similarity_threshold"]

    unique_items = []
    duplicate_count = 0

    for filtered_item in filtered_items:
        if is_duplicate(filtered_item["item"], existing_issues, threshold):
            duplicate_count += 1
            continue

        unique_items.append(filtered_item)

    print(f"✓ 重複: {duplicate_count}件")
    print(f"✓ 投稿対象: {len(unique_items)}件")
    print()

    # Phase 3: GitHub Issue 作成
    print("[Phase 3] GitHub Issue 作成")
    print("-" * 80)

    if not unique_items:
        print("投稿対象の記事がありません。")
        return

    created_issues = []

    for filtered_item in unique_items:
        item = filtered_item["item"]
        reliability_score = filtered_item["reliability_score"]
        matched_keywords = filtered_item["matched_keywords"]

        issue = create_github_issue(
            repo, item, reliability_score, matched_keywords, dry_run
        )

        if issue:
            created_issues.append(issue)

    print()
    print(f"✓ 作成されたIssue数: {len(created_issues)}件")
    print()

    # Project #15 に追加
    if not dry_run and created_issues:
        print("GitHub Project #15 に追加中...")
        print("-" * 80)

        success_count = 0
        for issue in created_issues:
            try:
                subprocess.run(
                    [
                        "gh",
                        "project",
                        "item-add",
                        str(project_number),
                        "--owner",
                        "YH-05",
                        "--url",
                        issue["url"],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                print(f"✓ Issue #{issue['number']} をProject #15に追加")
                success_count += 1
            except subprocess.CalledProcessError as e:
                print(f"✗ Issue #{issue['number']} の追加失敗: {e.stderr}")

        print()
        print(f"✓ Project追加成功: {success_count}/{len(created_issues)}件")
        print()

    # Phase 4: 結果報告
    print("[Phase 4] 結果報告")
    print("=" * 80)

    print(f"取得記事数: {len(items)}件")
    print("フィルタリング結果:")
    print(f"  - 投稿: {len(created_issues)}件")
    print(f"  - 除外: {excluded_count}件")
    print(f"  - 重複: {duplicate_count}件")
    print()

    if created_issues:
        print("作成されたIssue一覧:")
        for issue in created_issues:
            print(f"  - #{issue['number']}: {issue['title']}")
            print(f"    {issue['url']}")
        print()

    print(f"GitHub Project: https://github.com/users/YH-05/projects/{project_number}")
    print()
    print("完了しました！")


if __name__ == "__main__":
    main()
