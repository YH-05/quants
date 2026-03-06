# market.alternative

オルタナティブデータ（代替データ）を収集・分析するサブモジュール。
TSA（米国運輸保安局）の空港旅客数データなど、従来の株価・財務データを補完する
非伝統的な情報源から投資判断に役立つシグナルを取得します。

## クイックスタート

### TSA旅客数データの取得

```python
from market.alternative.tsa import TSAPassengerDataCollector

# コレクターを作成
collector = TSAPassengerDataCollector()

# 最新データを取得（全期間）
df = collector.scrape_tsa_passenger_data()

# 特定年のデータを取得（2019年以降が対象）
df_2024 = collector.scrape_tsa_passenger_data(year=2024)

print(df.head())
# 出力例:
#         Date   Numbers
# 0 2024-12-31  2485621
# 1 2024-12-30  2893012
# ...
```

### データサマリーの確認

```python
# サマリーを辞書として取得
summary = collector.get_data_summary(df)

# 整形済みのテキストとして出力
print(collector.format_summary(summary))
# 出力例:
# === TSA旅客数データ ===
# データ期間: 2019/01/01 - 2024/12/31
# データ件数: 2190件
# 最大旅客数: 2,893,012人 (2024/12/30)
# 最小旅客数: 87,534人 (2020/04/14)
# 平均旅客数: 1,854,321人
```

### SQLiteへの保存

```python
from pathlib import Path

db_path = Path("data/raw/tsa_passenger.db")

# 新しい日付のデータのみ追記保存（重複は自動スキップ）
collector.store_to_tsa_database(df, db_path=db_path)
```

### 可視化

```python
# DateをIndexに設定してからプロット
df_indexed = df.set_index("Date")
collector.plot_passenger_trend(df_indexed)
# 月次集計の棒グラフ（旅客数）+ 折れ線グラフ（前年比%）を表示
```

## 実装済み機能

### TSAPassengerDataCollector (`tsa.py`)

米国運輸保安局（TSA）公式サイト（tsa.gov）から空港通過旅客数を収集するクラス。
旅客数は航空需要・観光消費・経済活動の先行指標として利用できます。

| メソッド | 説明 | 戻り値 |
|---------|------|--------|
| `scrape_tsa_passenger_data(year=None)` | TSA.govから旅客数データをスクレイピング。`year` 省略時は最新データ全件取得 | `pd.DataFrame \| None` |
| `get_data_summary(df)` | 期間・最大/最小/平均旅客数などのサマリーを辞書で返す | `dict[str, str \| int \| float]` |
| `format_summary(summary)` | サマリー辞書を人間が読みやすいテキストに整形 | `str` |
| `save_to_csv(df, filename)` | DataFrameをCSVファイルに保存 | `None` |
| `store_to_tsa_database(df, db_path, table_name)` | SQLiteに差分保存（既存日付はスキップ） | `None` |
| `plot_passenger_trend(df, fig_save_path)` | 月次旅客数棒グラフ + 前年比折れ線グラフを描画 | `Figure \| None` |

#### scrape_tsa_passenger_data の詳細

```python
# 2019年以降の特定年を指定できる
df_2020 = collector.scrape_tsa_passenger_data(year=2020)
# -> 新型コロナ影響が顕著な2020年データを取得
```

- データ取得先: `https://www.tsa.gov/travel/passenger-volumes[/{year}]`
- 戻り値の列: `Date`（datetime型）、`Numbers`（int型、人数）
- 日付降順でソート済み

#### store_to_tsa_database の詳細

```python
# 初回実行: テーブルを新規作成して全データ挿入
# 2回目以降: DBに存在しない日付のデータのみを追記（差分更新）
collector.store_to_tsa_database(df, db_path="data/tsa.db", table_name="tsa_passenger")
```

#### get_data_summary の戻り値

```python
{
    "date_min": "2019/01/01",        # データ期間の開始日
    "date_max": "2024/12/31",        # データ期間の終了日
    "row_count": 2190,               # データ件数
    "max_passengers": 2893012,       # 最大旅客数
    "max_passengers_date": "2024/12/30",  # 最大旅客数の日付
    "min_passengers": 87534,         # 最小旅客数
    "min_passengers_date": "2020/04/14",  # 最小旅客数の日付
    "avg_passengers": 1854321.0,     # 平均旅客数
}
```

## 計画中の機能

| データソース | 概要 | 優先度 |
|-------------|------|--------|
| センチメント分析 | ソーシャルメディア・ニュースのセンチメントスコア | 高 |
| ESGデータ | 環境・社会・ガバナンス評価スコア | 高 |
| Webトラフィック | ウェブサイト・アプリの利用状況指標 | 中 |
| クレジットカードデータ | 集計済み消費動向データ | 中 |
| 衛星データ | 衛星画像を使った経済指標分析 | 低 |

## モジュール構成

```
market/alternative/
    __init__.py     # パッケージエクスポート
    README.md       # このファイル
    tsa.py          # TSA空港旅客数データ収集（実装済み）
```

## 関連モジュール

- [market パッケージ README](../README.md) - 市場データ取得パッケージの全体概要
- [market.yfinance](../yfinance/) - Yahoo Finance 株価・為替データ
- [market.fred](../fred/) - FRED 経済指標データ
