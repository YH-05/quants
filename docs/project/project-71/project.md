# Project 71: 日本株情報源の実装（Tier 1 + Tier 2）

## 概要

既存の `news_scraper` パッケージ（CNBC/NASDAQ/yfinance の3ソース、全て米国向け）に日本語 RSS ソースを追加し、`market` パッケージに J-Quants API / EDINET 開示 API クライアントを追加する。

## GitHub Project

- **Project URL**: https://github.com/users/YH-05/projects/71
- **Project Number**: 71

## Issue 一覧

| Issue | タイトル | Wave | 依存 | ステータス |
|-------|---------|------|------|-----------|
| #3738 | feat(news_scraper): 日本語 RSS スクレイパー（東洋経済・Investing.com・Yahoo!ニュース） | 1 | なし | Todo |
| #3739 | feat(news_scraper): JPX・TDnet RSS スクレイパー | 1 | なし | Todo |
| #3740 | feat(news_scraper): yfinance 日本株プリセット | 1 | なし | Todo |
| #3741 | feat(market): J-Quants API クライアント | 2 | なし | Todo |
| #3742 | feat(market): EDINET 開示 API クライアント | 2 | なし | Todo |
| #3743 | feat(news_scraper): 日本語ソース統合 | 3 | #3738, #3739, #3740 | Todo |
| #3744 | feat(market): market パッケージ統合 + RSS フィード登録 | 3 | #3741, #3742 | Todo |

## Wave 構成

```
Wave 1 (並行可能):           Wave 2 (Wave 1と並行可):
  #3738 東洋経済/Investing     #3741 J-Quants API
  #3739 JPX/TDnet              #3742 EDINET API
  #3740 yfinance JP
        |                            |
        v                            v
Wave 3:                        Wave 3:
  #3743 news_scraper 統合        #3744 market 統合
```

## 規模

- 新規ソースファイル: 19 ファイル（約2,620行）
- 変更ソースファイル: 9 ファイル（約445行 diff）
- 新規テストファイル: 18 ファイル（約3,985行）
- 合計: 約7,050行

## 設計判断

- `_DEFAULT_SOURCES` は変更しない（日本語ソースはオプトイン）
- J-Quants 認証はファイル永続化（`~/.jquants/token.json`）
- 新規 `edinet_api/` は既存 `edinet/` とは完全に別モジュール
- J-Quants キャッシュは既存 `market/cache/cache.py` の SQLiteCache を流用
