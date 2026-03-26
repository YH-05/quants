# 議論メモ: FREDヒストリカルデータ全シリーズ同期

**日付**: 2026-03-25
**議論ID**: disc-2026-03-25-fred-historical-sync
**参加**: ユーザー + AI

## 背景・コンテキスト

週次マーケットレポート・ディープリサーチ・バックテストで使用するFRED経済指標データの全量をローカルに保存し、API呼び出し削減とオフライン分析を可能にする。

## 実施内容

### 同期コマンド

```bash
uv run python -m market.fred.scripts.sync_historical --all
```

### 結果サマリー

| 項目 | 値 |
|------|-----|
| 同期シリーズ数 | 65/65 成功 |
| カテゴリ数 | 13 |
| 保存先 | `data/raw/fred/indicators/` |
| 合計サイズ | 24MB |
| ファイル数 | 64（63シリーズJSON + 1インデックス） |
| 最古データ | 1939年（PAYEMS） |
| 最新データ | 2026-03-24 |

### カテゴリ別シリーズ数

| カテゴリ | シリーズ数 |
|---------|----------|
| Prices | 3 |
| Interest Rates | 16 |
| Yield Spread | 7 |
| Corporate Bond Yield | 2 |
| Corporate Bond Yield Spread | 9 |
| Financial Data | 1 |
| Business & Economic Activity | 1 |
| Population, Employment, & Labor Force | 5 |
| Money, Banking, & Finance | 9 |
| Consumer Confidence | 2 |
| Developed Countries - Real GDP Level | 8 |
| Euro - Real GDP Level | 1 |
| Southeast Asia - Real GDP Level | 1 |

### 主要シリーズの詳細

| シリーズ | 説明 | データポイント | 期間 |
|---------|------|--------------|------|
| DFF | FF金利 | 26,199 | 1954-07 〜 2026-03 |
| DGS10 | 10年国債利回り | 16,039 | 1962-01 〜 2026-03 |
| DGS2 | 2年国債利回り | 12,447 | 1976-06 〜 2026-03 |
| T10Y2Y | 10年-2年スプレッド | 12,448 | 1976-06 〜 2026-03 |
| UNRATE | 失業率 | 937 | 1948-01 〜 2026-02 |
| CPIAUCSL | CPI | 949 | 1947-01 〜 2026-02 |
| PAYEMS | 非農業部門雇用者数 | 1,046 | 1939-01 〜 2026-02 |
| SP500 | S&P 500 | 2,513 | 2016-03 〜 2026-03 |
| VIXCLS | VIX | 9,149 | 1990-01 〜 2026-03 |
| GDPC1 | 実質GDP | 316 | 1947-01 〜 2025-10 |
| DAAA | AAA社債利回り | 10,850 | 1983-01 〜 2026-03 |
| SOFR | SOFR | 1,990 | 2018-04 〜 2026-03 |

## 決定事項

| ID | 内容 | コンテキスト |
|----|------|------------|
| dec-2026-03-25-001 | FRED全65シリーズのヒストリカルデータをJSON形式でローカルキャッシュに保存完了 | API呼び出し削減とオフライン分析を可能に |

## アクションアイテム

| ID | 内容 | 優先度 | ステータス |
|----|------|--------|----------|
| act-2026-03-25-001 | FRED自動同期の定期実行設定（`--auto --stale-hours 24`） | 中 | pending |
| act-2026-03-25-002 | SP500データ範囲確認（2016年以降のみ、補完要否調査） | 低 | pending |

## 今後のデータ更新方法

```bash
# インクリメンタル更新（24時間以上古いデータのみ）
uv run python -m market.fred.scripts.sync_historical --auto

# カテゴリ別更新
uv run python -m market.fred.scripts.sync_historical --category "Interest Rates"

# 個別シリーズ更新
uv run python -m market.fred.scripts.sync_historical --series DGS10

# ステータス確認
uv run python -m market.fred.scripts.sync_historical --status
```

## 技術的な補足

- **キャッシュ形式**: JSON（シリーズごとに1ファイル、date/valueペア + メタデータ）
- **インクリメンタル更新**: 既存データの最終日付以降のみFetch → マージ
- **環境変数**: `FRED_HISTORICAL_CACHE_DIR` でパス変更可能
- **設定ファイル**: `data/config/fred_series.json`
