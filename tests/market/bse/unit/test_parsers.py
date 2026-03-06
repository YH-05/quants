"""Unit tests for market.bse.parsers module.

Tests verify the JSON-to-ScripQuote parser, CSV-to-DataFrame parser,
and all numeric cleaning functions for the BSE API response format.

Test TODO List:
- [x] clean_price: normal price with commas
- [x] clean_price: negative price
- [x] clean_price: empty string returns None
- [x] clean_price: N/A returns None
- [x] clean_price: malformed value returns None
- [x] clean_price: infinity strings return None
- [x] clean_volume: comma-separated integer
- [x] clean_volume: empty string returns None
- [x] clean_volume: N/A returns None
- [x] clean_volume: malformed value returns None
- [x] clean_indian_number: standard number
- [x] clean_indian_number: Indian format (lakhs/crores)
- [x] clean_indian_number: empty string returns None
- [x] clean_indian_number: N/A returns None
- [x] clean_indian_number: malformed value returns None
- [x] clean_indian_number: infinity returns None
- [x] _create_cleaner: factory produces working cleaning function
- [x] _create_cleaner: factory-created function handles missing values
- [x] _create_cleaner: factory-created function handles conversion errors
- [x] _COLUMN_CLEANERS: mapping contains all expected columns
- [x] _COLUMN_CLEANERS: each cleaner is callable
- [x] _apply_numeric_cleaning: applies cleaners to DataFrame columns
- [x] _apply_numeric_cleaning: skips columns not present in DataFrame
- [x] parse_quote_response: valid response
- [x] parse_quote_response: missing required keys raises BseParseError
- [x] parse_quote_response: empty dict raises BseParseError
- [x] parse_quote_response: non-dict raises BseParseError
- [x] parse_historical_csv: valid CSV content
- [x] parse_historical_csv: empty CSV raises BseParseError
- [x] parse_historical_csv: bytes input (utf-8-sig)
- [x] parse_historical_csv: column renaming via COLUMN_NAME_MAP
- [x] Module exports: __all__ completeness
"""

import pandas as pd
import pytest

from market.bse.errors import BseParseError
from market.bse.parsers import (
    _COLUMN_CLEANERS,
    __all__,
    _apply_numeric_cleaning,
    _create_cleaner,
    clean_indian_number,
    clean_price,
    clean_volume,
    parse_historical_csv,
    parse_quote_response,
)

# =============================================================================
# Fixtures
# =============================================================================


def _make_quote_response(
    *,
    scrip_code: str = "500325",
    scrip_name: str = "RELIANCE INDUSTRIES LTD",
    scrip_group: str = "A",
    open_: str = "2450.00",
    high: str = "2480.50",
    low: str = "2440.00",
    close: str = "2470.25",
    last: str = "2469.90",
    prev_close: str = "2445.00",
    num_trades: str = "125000",
    num_shares: str = "5000000",
    net_turnover: str = "12345678900",
) -> dict:
    """Build a minimal BSE API quote response."""
    return {
        "ScripCode": scrip_code,
        "ScripName": scrip_name,
        "ScripGroup": scrip_group,
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "last": last,
        "PrevClose": prev_close,
        "No_Trades": num_trades,
        "No_of_Shrs": num_shares,
        "Net_Turnov": net_turnover,
    }


def _make_historical_csv(
    *,
    rows: list[dict[str, str]] | None = None,
) -> str:
    """Build a minimal BSE historical CSV content string."""
    if rows is None:
        rows = [
            {
                "ScripCode": "500325",
                "ScripName": "RELIANCE INDUSTRIES LTD",
                "Open": "2450.00",
                "High": "2480.50",
                "Low": "2440.00",
                "Close": "2470.25",
            },
        ]

    if not rows:
        return "ScripCode,ScripName,Open,High,Low,Close\n"

    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(row.values()))
    return "\n".join(lines) + "\n"


# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """parsers モジュールが正常にインポートできること。"""
        from market.bse import parsers

        assert parsers is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.bse import parsers

        for name in __all__:
            assert hasattr(parsers, name), f"{name} is not defined in parsers module"

    def test_正常系_allが11項目を含む(self) -> None:
        """__all__ が全11関数をエクスポートしていること。"""
        expected = {
            "clean_indian_number",
            "clean_price",
            "clean_volume",
            "parse_announcements",
            "parse_bhavcopy_csv",
            "parse_company_info",
            "parse_corporate_actions",
            "parse_financial_results",
            "parse_historical_csv",
            "parse_index_data",
            "parse_quote_response",
        }
        assert set(__all__) == expected


# =============================================================================
# clean_price
# =============================================================================


class TestCleanPrice:
    """clean_price のテスト。"""

    def test_正常系_カンマ付き価格を変換できる(self) -> None:
        """'2,450.00' を 2450.0 に変換できること。"""
        assert clean_price("2,450.00") == pytest.approx(2450.0)

    def test_正常系_カンマなしの価格を変換できる(self) -> None:
        """'2470.25' を 2470.25 に変換できること。"""
        assert clean_price("2470.25") == pytest.approx(2470.25)

    def test_正常系_負の価格を変換できる(self) -> None:
        """'-1.95' を -1.95 に変換できること。"""
        assert clean_price("-1.95") == pytest.approx(-1.95)

    def test_正常系_整数価格を変換できる(self) -> None:
        """'2450' を 2450.0 に変換できること。"""
        assert clean_price("2450") == pytest.approx(2450.0)

    def test_エッジケース_空文字でNoneを返す(self) -> None:
        """空文字で None を返すこと。"""
        assert clean_price("") is None

    def test_エッジケース_NAでNoneを返す(self) -> None:
        """'N/A' で None を返すこと。"""
        assert clean_price("N/A") is None

    def test_エッジケース_ハイフンでNoneを返す(self) -> None:
        """'-' で None を返すこと（BSE で欠損値として使用）。"""
        assert clean_price("-") is None

    def test_異常系_不正な値でNoneを返す(self) -> None:
        """パースできない文字列で None を返すこと。"""
        assert clean_price("abc") is None

    def test_エッジケース_スペースのみでNoneを返す(self) -> None:
        """空白文字のみで None を返すこと。"""
        assert clean_price("   ") is None

    def test_エッジケース_無限大文字列でNoneを返す(self) -> None:
        """'inf', '-inf', 'nan' で None を返すこと。"""
        assert clean_price("inf") is None
        assert clean_price("-inf") is None
        assert clean_price("nan") is None

    def test_エッジケース_ゼロを変換できる(self) -> None:
        """'0' を 0.0 に変換できること。"""
        assert clean_price("0") == pytest.approx(0.0)

    def test_エッジケース_na小文字バリエーション(self) -> None:
        """'na', 'NA', 'n/a' で None を返すこと。"""
        assert clean_price("NA") is None
        assert clean_price("n/a") is None


# =============================================================================
# clean_volume
# =============================================================================


class TestCleanVolume:
    """clean_volume のテスト。"""

    def test_正常系_カンマ区切り整数を変換できる(self) -> None:
        """'48,123,456' を 48123456 に変換できること。"""
        assert clean_volume("48,123,456") == 48123456

    def test_正常系_カンマなし整数を変換できる(self) -> None:
        """'5000000' を 5000000 に変換できること。"""
        assert clean_volume("5000000") == 5000000

    def test_エッジケース_空文字でNoneを返す(self) -> None:
        """空文字で None を返すこと。"""
        assert clean_volume("") is None

    def test_エッジケース_NAでNoneを返す(self) -> None:
        """'N/A' で None を返すこと。"""
        assert clean_volume("N/A") is None

    def test_異常系_不正な値でNoneを返す(self) -> None:
        """パースできない文字列で None を返すこと。"""
        assert clean_volume("abc") is None

    def test_正常系_ゼロを変換できる(self) -> None:
        """'0' を 0 に変換できること。"""
        assert clean_volume("0") == 0


# =============================================================================
# clean_indian_number
# =============================================================================


class TestCleanIndianNumber:
    """clean_indian_number のテスト。"""

    def test_正常系_標準数値を変換できる(self) -> None:
        """'1234567890' を 1234567890.0 に変換できること。"""
        assert clean_indian_number("1234567890") == pytest.approx(1234567890.0)

    def test_正常系_インド式カンマ区切りを変換できる(self) -> None:
        """'1,23,456' を 123456.0 に変換できること（lakhs形式）。"""
        assert clean_indian_number("1,23,456") == pytest.approx(123456.0)

    def test_正常系_crore形式を変換できる(self) -> None:
        """'12,34,56,789' を 123456789.0 に変換できること（crores形式）。"""
        assert clean_indian_number("12,34,56,789") == pytest.approx(123456789.0)

    def test_正常系_小数点付き数値を変換できる(self) -> None:
        """'1234.56' を 1234.56 に変換できること。"""
        assert clean_indian_number("1234.56") == pytest.approx(1234.56)

    def test_正常系_標準カンマ区切りも対応(self) -> None:
        """'1,234,567' を 1234567.0 に変換できること（標準カンマ区切り）。"""
        assert clean_indian_number("1,234,567") == pytest.approx(1234567.0)

    def test_エッジケース_空文字でNoneを返す(self) -> None:
        """空文字で None を返すこと。"""
        assert clean_indian_number("") is None

    def test_エッジケース_NAでNoneを返す(self) -> None:
        """'N/A' で None を返すこと。"""
        assert clean_indian_number("N/A") is None

    def test_エッジケース_ハイフンでNoneを返す(self) -> None:
        """'-' で None を返すこと。"""
        assert clean_indian_number("-") is None

    def test_異常系_不正な値でNoneを返す(self) -> None:
        """パースできない文字列で None を返すこと。"""
        assert clean_indian_number("abc") is None

    def test_エッジケース_無限大でNoneを返す(self) -> None:
        """'inf' で None を返すこと。"""
        assert clean_indian_number("inf") is None

    def test_正常系_ゼロを変換できる(self) -> None:
        """'0' を 0.0 に変換できること。"""
        assert clean_indian_number("0") == pytest.approx(0.0)

    def test_エッジケース_スペース付き数値を変換できる(self) -> None:
        """前後のスペースを無視して変換できること。"""
        assert clean_indian_number(" 1234 ") == pytest.approx(1234.0)


# =============================================================================
# _create_cleaner (factory function)
# =============================================================================


class TestCreateCleaner:
    """_create_cleaner ファクトリ関数のテスト。"""

    def test_正常系_ファクトリで生成した関数が正しく変換する(self) -> None:
        """ファクトリで float コンバータを持つ関数を生成し正しく動作すること。"""
        cleaner = _create_cleaner(
            converter=float,
            name="test_value",
            strip_chars=",",
        )
        assert cleaner("1,234.56") == pytest.approx(1234.56)

    def test_正常系_ファクトリで生成した関数がint変換できる(self) -> None:
        """ファクトリで int コンバータを持つ関数を生成し正しく動作すること。"""
        cleaner = _create_cleaner(
            converter=int,
            name="test_int",
            strip_chars=",",
        )
        assert cleaner("1,000") == 1000

    def test_エッジケース_ファクトリ関数が空文字でNoneを返す(self) -> None:
        """ファクトリで生成した関数が空文字で None を返すこと。"""
        cleaner = _create_cleaner(
            converter=float,
            name="test_value",
            strip_chars=",",
        )
        assert cleaner("") is None

    def test_エッジケース_ファクトリ関数がNAでNoneを返す(self) -> None:
        """ファクトリで生成した関数が N/A で None を返すこと。"""
        cleaner = _create_cleaner(
            converter=float,
            name="test_value",
        )
        assert cleaner("N/A") is None

    def test_異常系_ファクトリ関数が不正値でNoneを返す(self) -> None:
        """ファクトリで生成した関数がパース不可の値で None を返すこと。"""
        cleaner = _create_cleaner(
            converter=float,
            name="test_value",
        )
        assert cleaner("abc") is None

    def test_正常系_finiteチェックが有効な場合infでNoneを返す(self) -> None:
        """finite_check=True の場合 inf で None を返すこと。"""
        cleaner = _create_cleaner(
            converter=float,
            name="test_value",
            strip_chars="",
            finite_check=True,
        )
        assert cleaner("inf") is None


# =============================================================================
# _COLUMN_CLEANERS mapping
# =============================================================================


class TestColumnCleaners:
    """_COLUMN_CLEANERS マッピングのテスト。"""

    def test_正常系_9カラムのクリーナーが定義されている(self) -> None:
        """9つのカラムクリーナーが定義されていること。"""
        expected_columns = {
            "open",
            "high",
            "low",
            "close",
            "last",
            "prev_close",
            "num_trades",
            "num_shares",
            "net_turnover",
        }
        assert set(_COLUMN_CLEANERS.keys()) == expected_columns

    def test_正常系_各クリーナーがcallableである(self) -> None:
        """各クリーナーが呼び出し可能であること。"""
        for column, cleaner in _COLUMN_CLEANERS.items():
            assert callable(cleaner), f"Cleaner for '{column}' is not callable"


# =============================================================================
# _apply_numeric_cleaning
# =============================================================================


class TestApplyNumericCleaning:
    """_apply_numeric_cleaning 共通関数のテスト。"""

    def test_正常系_全カラムが正しくクリーニングされる(self) -> None:
        """全数値カラムが正しくクリーニングされること。"""
        df = pd.DataFrame(
            [
                {
                    "scrip_code": "500325",
                    "open": "2,450.00",
                    "high": "2,480.50",
                    "low": "2,440.00",
                    "close": "2,470.25",
                    "last": "2,469.90",
                    "prev_close": "2,445.00",
                    "num_trades": "125,000",
                    "num_shares": "5,000,000",
                    "net_turnover": "12,34,56,78,900",
                }
            ]
        )
        result = _apply_numeric_cleaning(df)

        assert result["open"].iloc[0] == pytest.approx(2450.0)
        assert result["high"].iloc[0] == pytest.approx(2480.5)
        assert result["low"].iloc[0] == pytest.approx(2440.0)
        assert result["close"].iloc[0] == pytest.approx(2470.25)
        assert result["last"].iloc[0] == pytest.approx(2469.9)
        assert result["prev_close"].iloc[0] == pytest.approx(2445.0)
        assert result["num_trades"].iloc[0] == 125000
        assert result["num_shares"].iloc[0] == 5000000

    def test_エッジケース_存在しないカラムはスキップされる(self) -> None:
        """DataFrame に存在しないカラムはスキップされること。"""
        df = pd.DataFrame(
            [
                {
                    "scrip_code": "500325",
                    "open": "2,450.00",
                }
            ]
        )
        result = _apply_numeric_cleaning(df)

        assert result["open"].iloc[0] == pytest.approx(2450.0)
        assert "volume" not in result.columns

    def test_正常系_文字列カラムは変更されない(self) -> None:
        """クリーニング対象外のカラムは変更されないこと。"""
        df = pd.DataFrame(
            [
                {
                    "scrip_code": "500325",
                    "scrip_name": "RELIANCE",
                    "open": "2,450.00",
                }
            ]
        )
        result = _apply_numeric_cleaning(df)

        assert result["scrip_code"].iloc[0] == "500325"
        assert result["scrip_name"].iloc[0] == "RELIANCE"


# =============================================================================
# parse_quote_response
# =============================================================================


class TestParseQuoteResponse:
    """parse_quote_response のテスト。"""

    def test_正常系_有効なレスポンスをScripQuoteに変換できる(self) -> None:
        """有効なレスポンスが正しく ScripQuote に変換されること。"""
        raw = _make_quote_response()
        quote = parse_quote_response(raw)

        assert quote.scrip_code == "500325"
        assert quote.scrip_name == "RELIANCE INDUSTRIES LTD"
        assert quote.scrip_group == "A"
        assert quote.open == "2450.00"
        assert quote.high == "2480.50"
        assert quote.low == "2440.00"
        assert quote.close == "2470.25"
        assert quote.last == "2469.90"
        assert quote.prev_close == "2445.00"
        assert quote.num_trades == "125000"
        assert quote.num_shares == "5000000"
        assert quote.net_turnover == "12345678900"

    def test_正常系_追加フィールドがあっても正常にパースできる(self) -> None:
        """レスポンスに追加フィールドがあっても必須フィールドは正しくパースされること。"""
        raw = _make_quote_response()
        raw["ExtraField"] = "extra_value"
        raw["AnotherField"] = 42

        quote = parse_quote_response(raw)

        assert quote.scrip_code == "500325"
        assert quote.scrip_name == "RELIANCE INDUSTRIES LTD"

    def test_異常系_空のdictでBseParseErrorを発生させる(self) -> None:
        """空の dict で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Empty quote response"):
            parse_quote_response({})

    def test_異常系_非dictでBseParseErrorを発生させる(self) -> None:
        """dict でない入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected dict"):
            parse_quote_response("not a dict")  # type: ignore[arg-type]

    def test_異常系_リスト入力でBseParseErrorを発生させる(self) -> None:
        """リスト入力で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Expected dict"):
            parse_quote_response([1, 2, 3])  # type: ignore[arg-type]

    def test_異常系_必須キー不足でBseParseErrorを発生させる(self) -> None:
        """必須キーが不足している場合に BseParseError が発生すること。"""
        incomplete = {"ScripCode": "500325", "ScripName": "RELIANCE"}

        with pytest.raises(BseParseError, match="Missing required keys"):
            parse_quote_response(incomplete)

    def test_正常系_数値型のScripCodeを文字列に変換できる(self) -> None:
        """数値型の ScripCode が文字列に変換されること。"""
        raw = _make_quote_response()
        raw["ScripCode"] = 500325  # int instead of str

        quote = parse_quote_response(raw)

        assert quote.scrip_code == "500325"
        assert isinstance(quote.scrip_code, str)


# =============================================================================
# parse_historical_csv
# =============================================================================


class TestParseHistoricalCsv:
    """parse_historical_csv のテスト。"""

    def test_正常系_有効なCSVをDataFrameに変換できる(self) -> None:
        """有効な CSV が正しく DataFrame に変換されること。"""
        csv_content = _make_historical_csv()
        df = parse_historical_csv(csv_content)

        assert len(df) == 1
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns
        # pandas auto-detects numeric types, so scrip_code may be int
        assert str(df["scrip_code"].iloc[0]) == "500325"

    def test_正常系_複数行のCSVを変換できる(self) -> None:
        """複数行の CSV が正しく DataFrame に変換されること。"""
        rows = [
            {
                "ScripCode": "500325",
                "ScripName": "RELIANCE",
                "Open": "2450.00",
                "High": "2480.50",
                "Low": "2440.00",
                "Close": "2470.25",
            },
            {
                "ScripCode": "500180",
                "ScripName": "HDFC BANK",
                "Open": "1650.00",
                "High": "1680.00",
                "Low": "1640.00",
                "Close": "1670.50",
            },
        ]
        csv_content = _make_historical_csv(rows=rows)
        df = parse_historical_csv(csv_content)

        assert len(df) == 2
        assert [str(x) for x in df["scrip_code"]] == ["500325", "500180"]

    def test_異常系_空のCSVでBseParseErrorを発生させる(self) -> None:
        """空の CSV で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Empty CSV"):
            parse_historical_csv("")

    def test_異常系_空白のみでBseParseErrorを発生させる(self) -> None:
        """空白のみの CSV で BseParseError が発生すること。"""
        with pytest.raises(BseParseError, match="Empty CSV"):
            parse_historical_csv("   \n  \n  ")

    def test_正常系_bytes入力をデコードできる(self) -> None:
        """bytes 入力（utf-8-sig）が正しくデコードされること。"""
        csv_content = _make_historical_csv()
        csv_bytes = b"\xef\xbb\xbf" + csv_content.encode("utf-8")

        df = parse_historical_csv(csv_bytes)

        assert len(df) == 1
        assert "scrip_code" in df.columns

    def test_正常系_カラム名がsnake_caseにリネームされる(self) -> None:
        """BSE API のカラム名が snake_case にリネームされること。"""
        csv_content = _make_historical_csv()
        df = parse_historical_csv(csv_content)

        # ScripCode -> scrip_code, ScripName -> scrip_name via COLUMN_NAME_MAP
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns
        assert "ScripCode" not in df.columns
        assert "ScripName" not in df.columns

    def test_正常系_数値カラムがクリーニングされる(self) -> None:
        """数値カラムが適切にクリーニングされること。"""
        csv_content = _make_historical_csv()
        df = parse_historical_csv(csv_content)

        # Open, High, Low, Close are in _COLUMN_CLEANERS
        assert df["open"].iloc[0] == pytest.approx(2450.0)
        assert df["high"].iloc[0] == pytest.approx(2480.5)
        assert df["low"].iloc[0] == pytest.approx(2440.0)
        assert df["close"].iloc[0] == pytest.approx(2470.25)

    def test_正常系_ヘッダのみのCSVで空DataFrameを返す(self) -> None:
        """ヘッダのみの CSV で空 DataFrame を返すこと。"""
        csv_content = _make_historical_csv(rows=[])
        df = parse_historical_csv(csv_content)

        assert len(df) == 0

    def test_正常系_カラム名の前後空白が除去される(self) -> None:
        """カラム名の前後空白が除去されること。"""
        csv_content = " ScripCode , ScripName , Open \n500325,RELIANCE,2450.00\n"
        df = parse_historical_csv(csv_content)

        # After stripping whitespace and renaming
        assert "scrip_code" in df.columns
        assert "scrip_name" in df.columns
