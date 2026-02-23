"""金融ニュース収集 CLI エントリポイント.

``python -m news_scraper`` で実行可能にするためのモジュール。

Examples
--------
>>> uv run python -m news_scraper --config data/config/news_scraper.yaml -v
>>> uv run python -m news_scraper -c data/config/news_scraper.yaml --sources cnbc nasdaq
"""

from .finance_news_collect import main

if __name__ == "__main__":
    main()
