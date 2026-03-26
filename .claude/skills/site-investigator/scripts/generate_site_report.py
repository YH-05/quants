"""サイト調査結果から JSON + Markdown レポートを生成するスクリプト.

Usage:
    uv run python .claude/skills/site-investigator/scripts/generate_site_report.py \
        --input .tmp/site-investigation-example-com.json \
        --output-dir .tmp/site-reports/example.com/
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from finance.utils.logging_config import get_logger

    logger = get_logger(__name__)
except ModuleNotFoundError:
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger = logging.getLogger(__name__)


def load_investigation_data(input_path: Path) -> dict[str, Any]:
    """調査結果 JSON を読み込む."""
    logger.info("Loading investigation data: %s", input_path)
    with input_path.open(encoding="utf-8") as f:
        return json.load(f)


def generate_json_report(data: dict[str, Any], output_path: Path) -> None:
    """構造化 JSON レポートを生成する."""
    report = {
        "url": data.get("url", ""),
        "investigated_at": data.get("investigated_at", datetime.now().isoformat()),
        "site_overview": data.get("site_overview", {}),
        "list_page": data.get("list_page", {}),
        "article_page": data.get("article_page", {}),
        "dynamic_behavior": data.get("dynamic_behavior", {}),
        "recommendations": data.get("recommendations", {}),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("JSON report generated: %s", output_path)


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "不明"
    return "あり" if value else "なし"


def _format_selector_table(selectors: dict[str, str | None]) -> str:
    """セレクタの辞書を Markdown テーブルに変換."""
    if not selectors:
        return "セレクタ情報なし\n"

    lines = ["| 要素 | セレクタ |", "|------|---------|"]
    for name, selector in selectors.items():
        display_name = {
            "article_container": "記事コンテナ",
            "title": "タイトル",
            "link": "リンク",
            "date": "日付",
            "author": "著者",
            "thumbnail": "サムネイル",
            "summary": "概要",
            "body": "本文",
            "category": "カテゴリ",
            "tags": "タグ",
            "related_articles": "関連記事",
            "comments": "コメント",
        }.get(name, name)
        lines.append(f"| {display_name} | `{selector or '未検出'}` |")
    return "\n".join(lines) + "\n"


def _format_pagination(pagination: dict[str, Any]) -> str:
    """ページネーション情報を整形."""
    if not pagination:
        return "ページネーション情報なし"

    ptype = pagination.get("type", "unknown")
    type_label = {
        "numbered": "番号付きページング",
        "next_prev": "次へ/前へボタン",
        "infinite_scroll": "無限スクロール",
        "load_more": "もっと見るボタン",
        "none": "なし（1ページ表示）",
    }.get(ptype, ptype)

    parts = [f"**方式**: {type_label}"]
    if pagination.get("next_selector"):
        parts.append(f"**次ページセレクタ**: `{pagination['next_selector']}`")
    if pagination.get("url_pattern"):
        parts.append(f"**URLパターン**: `{pagination['url_pattern']}`")
    return "\n".join(f"- {p}" for p in parts)


def _format_approach(approach: str | None) -> str:
    """スクレイピング手法名を日本語に."""
    return {
        "rss": "RSS フィード",
        "sitemap": "サイトマップ",
        "direct_scraping": "直接スクレイピング",
        "api": "API 直接呼び出し",
    }.get(approach or "", approach or "未定")


def generate_markdown_report(data: dict[str, Any], output_path: Path) -> None:
    """人間向け Markdown レポートを生成する."""
    url = data.get("url", "不明")
    investigated_at = data.get("investigated_at", "不明")
    overview = data.get("site_overview", {})
    list_page = data.get("list_page", {})
    article_page = data.get("article_page", {})
    dynamic = data.get("dynamic_behavior", {})
    recommendations = data.get("recommendations", {})

    # --- サイト概要 ---
    rss_urls = overview.get("rss_urls", [])
    rss_display = ", ".join(rss_urls) if rss_urls else "なし"
    robots = overview.get("robots_txt", {})

    sections = [
        f"# サイト調査レポート: {url}\n",
        f"調査日時: {investigated_at}\n",
        "## 1. サイト概要\n",
        "| 項目 | 値 |",
        "|------|-----|",
        f"| サイト種別 | {overview.get('type', '不明')} |",
        f"| 技術スタック | {overview.get('technology', '不明')} |",
        f"| 言語 | {overview.get('language', '不明')} |",
        f"| RSS | {_format_bool(overview.get('has_rss'))}（{rss_display}） |",
        f"| サイトマップ | {_format_bool(overview.get('has_sitemap'))} |",
        f"| robots.txt | {_format_bool(robots.get('exists'))} |",
        f"| ログイン要否 | {'必要' if overview.get('requires_login') else '不要'} |",
        f"| ペイウォール | {_format_bool(overview.get('has_paywall'))} |",
        "",
    ]

    # --- robots.txt 詳細 ---
    if robots.get("exists"):
        disallow = robots.get("disallow_rules", [])
        crawl_delay = robots.get("crawl_delay")
        sections.extend(
            [
                "### robots.txt 詳細\n",
                f"- **Disallow ルール**: {', '.join(f'`{r}`' for r in disallow) if disallow else 'なし'}",
                f"- **Crawl-delay**: {crawl_delay if crawl_delay else '指定なし'}",
                "",
            ]
        )

    # --- 一覧ページ ---
    if list_page:
        sections.extend(
            [
                "## 2. 一覧ページ構造\n",
                f"**URL**: {list_page.get('url', '不明')}\n",
                f"**1ページあたりの件数**: {list_page.get('items_per_page', '不明')}\n",
                "### セレクタ\n",
                _format_selector_table(list_page.get("selectors", {})),
                "",
                "### ページネーション\n",
                _format_pagination(list_page.get("pagination", {})),
                "",
                f"**記事 URL パターン**: `{list_page.get('url_pattern', '不明')}`\n",
            ]
        )

    # --- 記事ページ ---
    if article_page:
        sections.extend(
            [
                "## 3. 記事ページ構造\n",
                f"**サンプル URL**: {article_page.get('sample_url', '不明')}\n",
                "### セレクタ\n",
                _format_selector_table(article_page.get("selectors", {})),
                "",
            ]
        )

    # --- 動的挙動 ---
    sections.extend(
        [
            "## 4. 動的挙動\n",
            "| 項目 | 値 |",
            "|------|-----|",
            f"| SPA | {_format_bool(dynamic.get('is_spa'))} |",
            f"| フレームワーク | {dynamic.get('framework') or 'なし'} |",
            f"| 無限スクロール | {_format_bool(dynamic.get('has_infinite_scroll'))} |",
            f"| lazy load | {_format_bool(dynamic.get('has_lazy_load'))} |",
            f"| JS レンダリング必須 | {_format_bool(dynamic.get('requires_js_rendering'))} |",
            "",
        ]
    )

    api_endpoints = dynamic.get("api_endpoints", [])
    if api_endpoints:
        sections.extend(
            [
                "### 発見された API エンドポイント\n",
                *[f"- `{ep}`" for ep in api_endpoints],
                "",
            ]
        )

    # --- 推奨方針 ---
    sections.extend(
        [
            "## 5. スクレイピング推奨方針\n",
            f"1. **推奨**: {_format_approach(recommendations.get('best_approach'))}",
            f"2. **代替**: {_format_approach(recommendations.get('fallback_approach'))}",
            f"3. **レート制限**: {recommendations.get('rate_limit_suggestion', '1 req/sec')}",
            "",
        ]
    )

    notes = recommendations.get("notes", [])
    if notes:
        sections.extend(
            [
                "### 注意事項\n",
                *[f"- {note}" for note in notes],
                "",
            ]
        )

    # --- 書き出し ---
    content = "\n".join(sections)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Markdown report generated: %s", output_path)


def main() -> None:
    """エントリーポイント."""
    parser = argparse.ArgumentParser(
        description="サイト調査結果から JSON + Markdown レポートを生成"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="調査結果 JSON ファイルのパス",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="レポート出力ディレクトリ",
    )

    args = parser.parse_args()

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    data = load_investigation_data(args.input)
    logger.info("Investigation data loaded: %s", data.get("url"))

    # JSON レポート生成
    json_path = args.output_dir / "report.json"
    generate_json_report(data, json_path)

    # Markdown レポート生成
    md_path = args.output_dir / "report.md"
    generate_markdown_report(data, md_path)

    # スクリーンショットディレクトリ作成
    screenshots_dir = args.output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Report generation completed: %s, %s", json_path, md_path)
    print("\nレポート生成完了:")
    print(f"  JSON:     {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  Screenshots: {screenshots_dir}/")


if __name__ == "__main__":
    main()
