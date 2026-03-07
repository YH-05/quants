"""Unit tests for market.etfcom.collectors module.

TickerCollector, FundamentalsCollector, FundFlowsCollector の動作を検証する
テストスイート。

Test TODO List:
- [x] TickerCollector: デフォルト値で初期化
- [x] TickerCollector: カスタム browser / config で初期化
- [x] TickerCollector: DataCollector を継承していること
- [x] TickerCollector: name プロパティ
- [x] fetch(): pd.DataFrame を返却する
- [x] fetch(): 返却 DataFrame に必須カラムが含まれること
- [x] _parse_screener_table(): テーブル行をパースする
- [x] _parse_screener_table(): '--' を NaN に変換する
- [x] _parse_screener_table(): 空テーブルで空リスト
- [x] _rows_to_dataframe(): dict リストを DataFrame に変換する
- [x] _rows_to_dataframe(): 空リストで空 DataFrame
- [x] validate(): 空 DataFrame で False
- [x] validate(): 非空で ticker 列ありで True
- [x] validate(): ticker 列なしで False
- [x] browser がコンストラクタで注入可能であること
- [x] structlog ロガーの使用
- [x] __all__ エクスポート
- [x] FundamentalsCollector: デフォルト値で初期化
- [x] FundamentalsCollector: session/browser を注入できる
- [x] FundamentalsCollector: DataCollector を継承している
- [x] FundamentalsCollector: _parse_profile() で summary-data と classification-data を抽出
- [x] FundamentalsCollector: _parse_profile() で '--' を None に変換
- [x] FundamentalsCollector: _parse_profile() でデータなし時に空 dict
- [x] FundamentalsCollector: _get_html() curl_cffi 優先
- [x] FundamentalsCollector: _get_html() Playwright フォールバック
- [x] FundamentalsCollector: fetch() で複数ティッカーを逐次処理
- [x] FundamentalsCollector: validate() で必須カラム存在チェック
- [x] FundFlowsCollector: デフォルト値で初期化
- [x] FundFlowsCollector: session/browser を注入できる
- [x] FundFlowsCollector: DataCollector を継承している
- [x] FundFlowsCollector: _parse_fund_flows_table() でテーブルをパース
- [x] FundFlowsCollector: _parse_fund_flows_table() でカンマ区切り数値を変換
- [x] FundFlowsCollector: _parse_fund_flows_table() で '--' を NaN に変換
- [x] FundFlowsCollector: FUND_FLOWS_URL_TEMPLATE を使用して URL 構築
- [x] FundFlowsCollector: validate() で必須カラム存在チェック
- [x] __all__ に 3 つの Collector 全てがエクスポート
- [x] TickerNormalization: FundamentalsCollector が小文字を大文字に正規化
- [x] TickerNormalization: FundFlowsCollector が小文字を大文字に正規化
- [x] TickerNormalization: HistoricalFundFlowsCollector が小文字を大文字に正規化
- [x] FundamentalsCollector: 404 エラー時に minimal レコードが追加される
- [x] TickerValidation: 不正なティッカーで ValueError
- [x] TickerValidation: ハイフン付きティッカーで正常動作
- [x] FundFlowsCollector: 404 エラーが呼び出し元に伝播する
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from market.base_collector import DataCollector
from market.etfcom.errors import ETFComNotFoundError
from market.etfcom.types import RetryConfig, ScrapingConfig

# =============================================================================
# Required columns constant
# =============================================================================

REQUIRED_COLUMNS = {"ticker", "name", "issuer", "category", "expense_ratio", "aum"}

# =============================================================================
# Sample HTML fixtures
# =============================================================================

SAMPLE_SCREENER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><title>ETF Screener | ETF.com</title></head>
<body>
<div id="etf-screener">
  <table class="screener-table">
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Fund Name</th>
        <th>Issuer</th>
        <th>Segment</th>
        <th>Expense Ratio</th>
        <th>AUM</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><a href="/SPY">SPY</a></td>
        <td>SPDR S&amp;P 500 ETF Trust</td>
        <td>State Street</td>
        <td>Equity: U.S. - Large Cap</td>
        <td>0.09%</td>
        <td>$500.00B</td>
      </tr>
      <tr>
        <td><a href="/VOO">VOO</a></td>
        <td>Vanguard S&amp;P 500 ETF</td>
        <td>Vanguard</td>
        <td>Equity: U.S. - Large Cap</td>
        <td>0.03%</td>
        <td>$751.49B</td>
      </tr>
      <tr>
        <td><a href="/QQQ">QQQ</a></td>
        <td>Invesco QQQ Trust</td>
        <td>Invesco</td>
        <td>Equity: U.S. - Large Cap Growth</td>
        <td>0.20%</td>
        <td>$280.00B</td>
      </tr>
    </tbody>
  </table>
</div>
</body>
</html>"""

SAMPLE_SCREENER_HTML_WITH_PLACEHOLDER = """\
<!DOCTYPE html>
<html lang="en">
<body>
<table class="screener-table">
  <thead>
    <tr>
      <th>Ticker</th>
      <th>Fund Name</th>
      <th>Issuer</th>
      <th>Segment</th>
      <th>Expense Ratio</th>
      <th>AUM</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="/SPY">SPY</a></td>
      <td>SPDR S&amp;P 500 ETF Trust</td>
      <td>State Street</td>
      <td>Equity: U.S. - Large Cap</td>
      <td>0.09%</td>
      <td>$500.00B</td>
    </tr>
    <tr>
      <td><a href="/PFFL">PFFL</a></td>
      <td>ETRACS 2xMonthly Pay Leveraged Preferred Stock</td>
      <td>--</td>
      <td>--</td>
      <td>--</td>
      <td>--</td>
    </tr>
  </tbody>
</table>
</body>
</html>"""

SAMPLE_EMPTY_TABLE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<body>
<table class="screener-table">
  <thead>
    <tr>
      <th>Ticker</th>
      <th>Fund Name</th>
      <th>Issuer</th>
      <th>Segment</th>
      <th>Expense Ratio</th>
      <th>AUM</th>
    </tr>
  </thead>
  <tbody>
  </tbody>
</table>
</body>
</html>"""


# =============================================================================
# Initialization tests
# =============================================================================


class TestTickerCollectorInit:
    """TickerCollector 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの config で初期化されること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        assert collector._config is not None
        assert isinstance(collector._config, ScrapingConfig)

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム ScrapingConfig で初期化されること。"""
        from market.etfcom.collectors import TickerCollector

        config = ScrapingConfig(polite_delay=5.0, headless=False)
        collector = TickerCollector(config=config)

        assert collector._config.polite_delay == 5.0
        assert collector._config.headless is False

    def test_正常系_browserを注入できる(self) -> None:
        """外部から browser を注入できること（DI パターン）。"""
        from market.etfcom.collectors import TickerCollector

        mock_browser = AsyncMock()
        collector = TickerCollector(browser=mock_browser)

        assert collector._browser_instance is mock_browser

    def test_正常系_browser_Noneでデフォルト(self) -> None:
        """browser=None の場合 _browser_instance が None であること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        assert collector._browser_instance is None

    def test_正常系_DataCollectorを継承している(self) -> None:
        """TickerCollector が DataCollector を継承していること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        assert isinstance(collector, DataCollector)

    def test_正常系_nameプロパティがTickerCollectorを返す(self) -> None:
        """name プロパティが 'TickerCollector' を返すこと。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        assert collector.name == "TickerCollector"


# =============================================================================
# _parse_screener_table() tests
# =============================================================================


class TestParseScreenerTable:
    """_parse_screener_table() のテスト。"""

    def test_正常系_テーブル行をパースする(self) -> None:
        """HTML テーブルから ETF 行を正しくパースすること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows = collector._parse_screener_table(SAMPLE_SCREENER_HTML)

        assert len(rows) == 3
        assert rows[0]["ticker"] == "SPY"
        assert rows[0]["name"] == "SPDR S&P 500 ETF Trust"
        assert rows[1]["ticker"] == "VOO"
        assert rows[2]["ticker"] == "QQQ"

    def test_正常系_プレースホルダをNoneに変換する(self) -> None:
        """'--' プレースホルダーが None に変換されること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows = collector._parse_screener_table(SAMPLE_SCREENER_HTML_WITH_PLACEHOLDER)

        assert len(rows) == 2
        # PFFL row has '--' placeholders
        pffl_row = rows[1]
        assert pffl_row["ticker"] == "PFFL"
        assert pffl_row["issuer"] is None
        assert pffl_row["category"] is None
        assert pffl_row["expense_ratio"] is None
        assert pffl_row["aum"] is None

    def test_正常系_空テーブルで空リスト(self) -> None:
        """空のテーブルから空リストが返ること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows = collector._parse_screener_table(SAMPLE_EMPTY_TABLE_HTML)

        assert rows == []

    def test_正常系_テーブルなしのHTMLで空リスト(self) -> None:
        """テーブルが存在しない HTML から空リストが返ること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows = collector._parse_screener_table(
            "<html><body>No table here</body></html>"
        )

        assert rows == []


# =============================================================================
# _rows_to_dataframe() tests
# =============================================================================


class TestRowsToDataframe:
    """_rows_to_dataframe() のテスト。"""

    def test_正常系_dictリストをDataFrameに変換する(self) -> None:
        """dict のリストが pd.DataFrame に正しく変換されること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows: list[dict[str, str | None]] = [
            {
                "ticker": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "issuer": "State Street",
                "category": "Equity: U.S. - Large Cap",
                "expense_ratio": "0.09%",
                "aum": "$500.00B",
            },
            {
                "ticker": "VOO",
                "name": "Vanguard S&P 500 ETF",
                "issuer": "Vanguard",
                "category": "Equity: U.S. - Large Cap",
                "expense_ratio": "0.03%",
                "aum": "$751.49B",
            },
        ]

        df = collector._rows_to_dataframe(rows)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert set(REQUIRED_COLUMNS).issubset(set(df.columns))
        assert df["ticker"].tolist() == ["SPY", "VOO"]

    def test_正常系_空リストで空DataFrame(self) -> None:
        """空リストから空 DataFrame が返ること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        df = collector._rows_to_dataframe([])

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_正常系_NoneがNaNに変換される(self) -> None:
        """None 値が NaN に変換されること。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        rows = [
            {
                "ticker": "PFFL",
                "name": "ETRACS 2xMonthly Pay",
                "issuer": None,
                "category": None,
                "expense_ratio": None,
                "aum": None,
            },
        ]

        df = collector._rows_to_dataframe(rows)

        assert len(df) == 1
        assert df["ticker"].iloc[0] == "PFFL"
        assert pd.isna(df["issuer"].iloc[0])
        assert pd.isna(df["expense_ratio"].iloc[0])


# =============================================================================
# validate() tests
# =============================================================================


class TestValidate:
    """validate() のテスト。"""

    def test_正常系_非空でticker列ありでTrue(self) -> None:
        """非空 DataFrame で ticker 列がある場合 True を返すこと。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        df = pd.DataFrame(
            {
                "ticker": ["SPY", "VOO"],
                "name": ["SPDR S&P 500", "Vanguard S&P 500"],
                "issuer": ["State Street", "Vanguard"],
                "category": ["Large Cap", "Large Cap"],
                "expense_ratio": ["0.09%", "0.03%"],
                "aum": ["$500B", "$751B"],
            }
        )

        assert collector.validate(df) is True

    def test_異常系_空DataFrameでFalse(self) -> None:
        """空 DataFrame で False を返すこと。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        df = pd.DataFrame()

        assert collector.validate(df) is False

    def test_異常系_ticker列なしでFalse(self) -> None:
        """ticker 列がない DataFrame で False を返すこと。"""
        from market.etfcom.collectors import TickerCollector

        collector = TickerCollector()
        df = pd.DataFrame(
            {
                "name": ["SPDR S&P 500"],
                "issuer": ["State Street"],
            }
        )

        assert collector.validate(df) is False


# =============================================================================
# fetch() tests (via _async_fetch)
# =============================================================================


class TestFetch:
    """fetch() / _async_fetch() のテスト。"""

    @pytest.mark.asyncio
    async def test_正常系_DataFrameを返却する(self) -> None:
        """_async_fetch() が pd.DataFrame を返却すること。"""
        from market.etfcom.collectors import TickerCollector

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value=SAMPLE_SCREENER_HTML)
        mock_page.query_selector = AsyncMock(return_value=None)  # no next page
        mock_page.close = AsyncMock()

        mock_browser._ensure_browser = AsyncMock()
        mock_browser._navigate = AsyncMock(return_value=mock_page)
        mock_browser._accept_cookies = AsyncMock()
        mock_browser._click_display_100 = AsyncMock()
        mock_browser.close = AsyncMock()

        config = ScrapingConfig(
            polite_delay=0.0,
            delay_jitter=0.0,
            timeout=5.0,
            stability_wait=0.0,
        )
        collector = TickerCollector(browser=mock_browser, config=config)

        with patch("market.etfcom.collectors.asyncio.sleep", new_callable=AsyncMock):
            df = await collector._async_fetch()

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "ticker" in df.columns

    @pytest.mark.asyncio
    async def test_正常系_必須カラムが含まれること(self) -> None:
        """返却 DataFrame に必須カラムが全て含まれること。"""
        from market.etfcom.collectors import TickerCollector

        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value=SAMPLE_SCREENER_HTML)
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.close = AsyncMock()

        mock_browser._ensure_browser = AsyncMock()
        mock_browser._navigate = AsyncMock(return_value=mock_page)
        mock_browser._accept_cookies = AsyncMock()
        mock_browser._click_display_100 = AsyncMock()
        mock_browser.close = AsyncMock()

        config = ScrapingConfig(
            polite_delay=0.0,
            delay_jitter=0.0,
            timeout=5.0,
            stability_wait=0.0,
        )
        collector = TickerCollector(browser=mock_browser, config=config)

        with patch("market.etfcom.collectors.asyncio.sleep", new_callable=AsyncMock):
            df = await collector._async_fetch()

        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing required column: {col}"

    @pytest.mark.asyncio
    async def test_正常系_ページネーションで複数ページ取得(self) -> None:
        """複数ページのデータを結合して返すこと。"""
        from market.etfcom.collectors import TickerCollector

        mock_browser = AsyncMock()
        mock_page = AsyncMock()

        # First call returns HTML with next button, second returns without
        mock_page.content = AsyncMock(
            side_effect=[SAMPLE_SCREENER_HTML, SAMPLE_SCREENER_HTML]
        )

        # First query returns a next button, second returns None
        mock_next_button = AsyncMock()
        mock_next_button.click = AsyncMock()
        mock_page.query_selector = AsyncMock(side_effect=[mock_next_button, None])
        mock_page.close = AsyncMock()

        mock_browser._ensure_browser = AsyncMock()
        mock_browser._navigate = AsyncMock(return_value=mock_page)
        mock_browser._accept_cookies = AsyncMock()
        mock_browser._click_display_100 = AsyncMock()
        mock_browser.close = AsyncMock()

        config = ScrapingConfig(
            polite_delay=0.0,
            delay_jitter=0.0,
            timeout=5.0,
            stability_wait=0.0,
        )
        collector = TickerCollector(browser=mock_browser, config=config)

        with patch("market.etfcom.collectors.asyncio.sleep", new_callable=AsyncMock):
            df = await collector._async_fetch()

        # 3 rows per page x 2 pages = 6 rows
        assert len(df) == 6


# =============================================================================
# Logging tests
# =============================================================================


class TestLogging:
    """ロギングのテスト。"""

    def test_正常系_loggerが定義されている(self) -> None:
        """モジュールレベルで structlog ロガーが定義されていること。"""
        import market.etfcom.collectors as collectors_module

        assert hasattr(collectors_module, "logger")


# =============================================================================
# __all__ export tests
# =============================================================================


class TestModuleExports:
    """__all__ エクスポートのテスト。"""

    def test_正常系_TickerCollectorがエクスポートされている(self) -> None:
        """__all__ に TickerCollector が含まれていること。"""
        from market.etfcom.collectors import __all__

        assert "TickerCollector" in __all__

    def test_正常系_3つのCollector全てがエクスポートされている(self) -> None:
        """__all__ に TickerCollector, FundamentalsCollector, FundFlowsCollector が含まれていること。"""
        from market.etfcom.collectors import __all__

        assert "TickerCollector" in __all__
        assert "FundamentalsCollector" in __all__
        assert "FundFlowsCollector" in __all__


# =============================================================================
# Sample HTML fixtures for FundamentalsCollector
# =============================================================================

SAMPLE_PROFILE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><title>SPY | SPDR S&amp;P 500 ETF Trust | ETF.com</title></head>
<body>
<div data-testid="summary-data">
  <table>
    <tbody>
      <tr><td>Issuer</td><td>State Street</td></tr>
      <tr><td>Inception Date</td><td>01/22/93</td></tr>
      <tr><td>Expense Ratio</td><td>0.09%</td></tr>
      <tr><td>AUM</td><td>$500.00B</td></tr>
      <tr><td>Index Tracked</td><td>S&amp;P 500</td></tr>
    </tbody>
  </table>
</div>
<div data-testid="classification-data">
  <table>
    <tbody>
      <tr><td>Segment</td><td>MSCI USA Large Cap</td></tr>
      <tr><td>Structure</td><td>Unit Investment Trust</td></tr>
      <tr><td>Asset Class</td><td>Equity</td></tr>
      <tr><td>Category</td><td>Size and Style</td></tr>
      <tr><td>Focus</td><td>Large Cap</td></tr>
      <tr><td>Niche</td><td>Broad-based</td></tr>
      <tr><td>Region</td><td>North America</td></tr>
      <tr><td>Geography</td><td>U.S.</td></tr>
      <tr><td>Weighting Methodology</td><td>Market Cap</td></tr>
      <tr><td>Selection Methodology</td><td>Committee</td></tr>
      <tr><td>Segment Benchmark</td><td>MSCI USA Large Cap</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>"""

SAMPLE_PROFILE_HTML_WITH_PLACEHOLDER = """\
<!DOCTYPE html>
<html lang="en">
<body>
<div data-testid="summary-data">
  <table>
    <tbody>
      <tr><td>Issuer</td><td>--</td></tr>
      <tr><td>Inception Date</td><td>--</td></tr>
      <tr><td>Expense Ratio</td><td>--</td></tr>
      <tr><td>AUM</td><td>--</td></tr>
      <tr><td>Index Tracked</td><td>--</td></tr>
    </tbody>
  </table>
</div>
<div data-testid="classification-data">
  <table>
    <tbody>
      <tr><td>Segment</td><td>--</td></tr>
      <tr><td>Structure</td><td>--</td></tr>
      <tr><td>Asset Class</td><td>--</td></tr>
      <tr><td>Category</td><td>--</td></tr>
      <tr><td>Focus</td><td>--</td></tr>
      <tr><td>Niche</td><td>--</td></tr>
      <tr><td>Region</td><td>--</td></tr>
      <tr><td>Geography</td><td>--</td></tr>
      <tr><td>Weighting Methodology</td><td>--</td></tr>
      <tr><td>Selection Methodology</td><td>--</td></tr>
      <tr><td>Segment Benchmark</td><td>--</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>"""

SAMPLE_PROFILE_HTML_NO_DATA = """\
<!DOCTYPE html>
<html lang="en">
<body>
<div>No profile data here</div>
</body>
</html>"""


# =============================================================================
# Sample HTML fixtures for FundFlowsCollector
# =============================================================================

SAMPLE_FUND_FLOWS_HTML = """\
<!DOCTYPE html>
<html lang="en">
<body>
<div data-testid="fund-flows-table">
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Net Flows ($M)</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>2025-09-10</td><td>2,787.59</td></tr>
      <tr><td>2025-09-09</td><td>-1,234.56</td></tr>
      <tr><td>2025-09-08</td><td>-104.61</td></tr>
      <tr><td>2025-09-05</td><td>3,456.78</td></tr>
      <tr><td>2025-09-04</td><td>987.65</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>"""

SAMPLE_FUND_FLOWS_HTML_WITH_PLACEHOLDER = """\
<!DOCTYPE html>
<html lang="en">
<body>
<div data-testid="fund-flows-table">
  <table>
    <thead>
      <tr><th>Date</th><th>Net Flows ($M)</th></tr>
    </thead>
    <tbody>
      <tr><td>2025-09-10</td><td>2,787.59</td></tr>
      <tr><td>2025-09-09</td><td>--</td></tr>
      <tr><td>2025-09-08</td><td>0.00</td></tr>
    </tbody>
  </table>
</div>
</body>
</html>"""

SAMPLE_FUND_FLOWS_HTML_NO_TABLE = """\
<!DOCTYPE html>
<html lang="en">
<body>
<div>No fund flows data here</div>
</body>
</html>"""


# =============================================================================
# FundamentalsCollector Initialization tests
# =============================================================================


class TestFundamentalsCollectorInit:
    """FundamentalsCollector 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの config で初期化されること。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        assert collector._config is not None
        assert isinstance(collector._config, ScrapingConfig)
        assert collector._retry_config is not None
        assert isinstance(collector._retry_config, RetryConfig)

    def test_正常系_session_browserを注入できる(self) -> None:
        """外部から session と browser を注入できること（DI パターン）。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_browser = AsyncMock()
        collector = FundamentalsCollector(session=mock_session, browser=mock_browser)

        assert collector._session_instance is mock_session
        assert collector._browser_instance is mock_browser

    def test_正常系_DataCollectorを継承している(self) -> None:
        """FundamentalsCollector が DataCollector を継承していること。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        assert isinstance(collector, DataCollector)

    def test_正常系_nameプロパティがFundamentalsCollectorを返す(self) -> None:
        """name プロパティが 'FundamentalsCollector' を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        assert collector.name == "FundamentalsCollector"

    def test_正常系_カスタムconfigで初期化できる(self) -> None:
        """カスタム ScrapingConfig と RetryConfig で初期化されること。"""
        from market.etfcom.collectors import FundamentalsCollector

        config = ScrapingConfig(polite_delay=5.0, headless=False)
        retry_config = RetryConfig(max_attempts=5)
        collector = FundamentalsCollector(config=config, retry_config=retry_config)

        assert collector._config.polite_delay == 5.0
        assert collector._retry_config.max_attempts == 5


# =============================================================================
# FundamentalsCollector _parse_profile() tests
# =============================================================================


class TestParseProfile:
    """FundamentalsCollector._parse_profile() のテスト。"""

    def test_正常系_summaryとclassificationデータを抽出する(self) -> None:
        """summary-data と classification-data の両方からデータを抽出すること。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        result = collector._parse_profile(SAMPLE_PROFILE_HTML, "SPY")

        assert result["ticker"] == "SPY"
        assert result["issuer"] == "State Street"
        assert result["inception_date"] == "01/22/93"
        assert result["expense_ratio"] == "0.09%"
        assert result["aum"] == "$500.00B"
        assert result["index_tracked"] == "S&P 500"
        assert result["segment"] == "MSCI USA Large Cap"
        assert result["structure"] == "Unit Investment Trust"
        assert result["asset_class"] == "Equity"
        assert result["category"] == "Size and Style"
        assert result["focus"] == "Large Cap"
        assert result["niche"] == "Broad-based"
        assert result["region"] == "North America"
        assert result["geography"] == "U.S."

    def test_正常系_プレースホルダをNoneに変換する(self) -> None:
        """'--' プレースホルダーが None に変換されること。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        result = collector._parse_profile(SAMPLE_PROFILE_HTML_WITH_PLACEHOLDER, "PFFL")

        assert result["ticker"] == "PFFL"
        assert result["issuer"] is None
        assert result["inception_date"] is None
        assert result["expense_ratio"] is None
        assert result["aum"] is None
        assert result["segment"] is None

    def test_正常系_データなし時に空dict(self) -> None:
        """summary-data も classification-data も存在しない場合、ticker のみの dict を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        result = collector._parse_profile(SAMPLE_PROFILE_HTML_NO_DATA, "XYZ")

        assert result["ticker"] == "XYZ"
        # No other data fields should be present beyond ticker
        assert len(result) == 1


# =============================================================================
# FundamentalsCollector _get_html() tests
# =============================================================================


class TestFundamentalsGetHtml:
    """FundamentalsCollector._get_html() のテスト。"""

    def test_正常系_curl_cffi優先で取得する(self) -> None:
        """curl_cffi のレスポンスが十分な場合、Playwright を使わないこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_PROFILE_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        mock_browser = AsyncMock()

        collector = FundamentalsCollector(session=mock_session, browser=mock_browser)
        html = collector._get_html("https://www.etf.com/SPY")

        assert html == SAMPLE_PROFILE_HTML
        mock_session.get_with_retry.assert_called_once()
        # Browser should not be called
        mock_browser._get_page_html_with_retry.assert_not_called()

    def test_正常系_Playwrightフォールバック(self) -> None:
        """curl_cffi が ETFComBlockedError を発生させた場合、Playwright にフォールバックすること。"""
        from market.etfcom.collectors import FundamentalsCollector
        from market.etfcom.errors import ETFComBlockedError

        mock_session = MagicMock()
        mock_session.get_with_retry.side_effect = ETFComBlockedError(
            "Blocked", url="https://www.etf.com/SPY", status_code=403
        )

        mock_browser = AsyncMock()
        mock_browser._ensure_browser = AsyncMock()
        mock_browser._get_page_html_with_retry = AsyncMock(
            return_value=SAMPLE_PROFILE_HTML
        )

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(
            session=mock_session, browser=mock_browser, config=config
        )
        html = collector._get_html("https://www.etf.com/SPY")

        assert html == SAMPLE_PROFILE_HTML
        mock_browser._get_page_html_with_retry.assert_called_once()

    def test_正常系_空コンテンツでPlaywrightフォールバック(self) -> None:
        """curl_cffi のレスポンスが短い場合、Playwright にフォールバックすること。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""  # Empty content
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        mock_browser = AsyncMock()
        mock_browser._ensure_browser = AsyncMock()
        mock_browser._get_page_html_with_retry = AsyncMock(
            return_value=SAMPLE_PROFILE_HTML
        )

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(
            session=mock_session, browser=mock_browser, config=config
        )
        html = collector._get_html("https://www.etf.com/SPY")

        assert html == SAMPLE_PROFILE_HTML
        mock_browser._get_page_html_with_retry.assert_called_once()


# =============================================================================
# FundamentalsCollector fetch() tests
# =============================================================================


class TestFundamentalsFetch:
    """FundamentalsCollector.fetch() のテスト。"""

    def test_正常系_複数ティッカーを逐次処理できる(self) -> None:
        """tickers 引数で複数ティッカーを渡し、逐次処理して DataFrame を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_PROFILE_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["SPY", "VOO"])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ticker" in df.columns
        assert set(df["ticker"].tolist()) == {"SPY", "VOO"}

    def test_正常系_単一ティッカーでDataFrameを返す(self) -> None:
        """tickers に1つだけ渡した場合も DataFrame を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_PROFILE_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["SPY"])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df["ticker"].iloc[0] == "SPY"

    def test_正常系_空のtickersリストで空DataFrame(self) -> None:
        """空のティッカーリストで空 DataFrame を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()

        df = collector.fetch(tickers=[])

        assert isinstance(df, pd.DataFrame)
        assert df.empty


# =============================================================================
# FundamentalsCollector validate() tests
# =============================================================================


class TestFundamentalsValidate:
    """FundamentalsCollector.validate() のテスト。"""

    def test_正常系_必須カラムが存在してTrue(self) -> None:
        """必須カラムが全て存在する DataFrame で True を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        df = pd.DataFrame(
            {
                "ticker": ["SPY"],
                "issuer": ["State Street"],
                "expense_ratio": ["0.09%"],
                "aum": ["$500B"],
            }
        )

        assert collector.validate(df) is True

    def test_異常系_空DataFrameでFalse(self) -> None:
        """空 DataFrame で False を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        df = pd.DataFrame()

        assert collector.validate(df) is False

    def test_異常系_ticker列なしでFalse(self) -> None:
        """ticker 列がない DataFrame で False を返すこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        collector = FundamentalsCollector()
        df = pd.DataFrame({"issuer": ["State Street"]})

        assert collector.validate(df) is False


# =============================================================================
# FundFlowsCollector Initialization tests
# =============================================================================


class TestFundFlowsCollectorInit:
    """FundFlowsCollector 初期化のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルトの config で初期化されること。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        assert collector._config is not None
        assert isinstance(collector._config, ScrapingConfig)

    def test_正常系_session_browserを注入できる(self) -> None:
        """外部から session と browser を注入できること（DI パターン）。"""
        from market.etfcom.collectors import FundFlowsCollector

        mock_session = MagicMock()
        mock_browser = AsyncMock()
        collector = FundFlowsCollector(session=mock_session, browser=mock_browser)

        assert collector._session_instance is mock_session
        assert collector._browser_instance is mock_browser

    def test_正常系_DataCollectorを継承している(self) -> None:
        """FundFlowsCollector が DataCollector を継承していること。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        assert isinstance(collector, DataCollector)

    def test_正常系_nameプロパティがFundFlowsCollectorを返す(self) -> None:
        """name プロパティが 'FundFlowsCollector' を返すこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        assert collector.name == "FundFlowsCollector"


# =============================================================================
# FundFlowsCollector _parse_fund_flows_table() tests
# =============================================================================


class TestParseFundFlowsTable:
    """FundFlowsCollector._parse_fund_flows_table() のテスト。"""

    def test_正常系_テーブルを正しくパースする(self) -> None:
        """fund-flows-table からデータを正しくパースすること。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        rows = collector._parse_fund_flows_table(SAMPLE_FUND_FLOWS_HTML)

        assert len(rows) == 5
        assert rows[0]["date"] == "2025-09-10"
        assert rows[0]["net_flows"] == 2787.59
        assert rows[1]["net_flows"] == -1234.56

    def test_正常系_カンマ区切り数値を正しく変換する(self) -> None:
        """カンマ区切りの数値（"2,787.59"）を float に正しく変換すること。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        rows = collector._parse_fund_flows_table(SAMPLE_FUND_FLOWS_HTML)

        # First row: "2,787.59" -> 2787.59
        assert rows[0]["net_flows"] == pytest.approx(2787.59)
        # Second row: "-1,234.56" -> -1234.56
        assert rows[1]["net_flows"] == pytest.approx(-1234.56)

    def test_正常系_プレースホルダをNaNに変換する(self) -> None:
        """'--' プレースホルダーが NaN に変換されること。"""
        from math import isnan

        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        rows = collector._parse_fund_flows_table(
            SAMPLE_FUND_FLOWS_HTML_WITH_PLACEHOLDER
        )

        assert len(rows) == 3
        # Second row has '--' for net_flows
        assert isnan(rows[1]["net_flows"])

    def test_正常系_テーブルなし時に空リスト(self) -> None:
        """fund-flows-table が存在しない HTML で空リストを返すこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        rows = collector._parse_fund_flows_table(SAMPLE_FUND_FLOWS_HTML_NO_TABLE)

        assert rows == []


# =============================================================================
# FundFlowsCollector _get_html() tests
# =============================================================================


class TestFundFlowsGetHtml:
    """FundFlowsCollector._get_html() のテスト。"""

    def test_正常系_curl_cffi優先で取得する(self) -> None:
        """curl_cffi のレスポンスが十分な場合、Playwright を使わないこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_FUND_FLOWS_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        mock_browser = AsyncMock()

        collector = FundFlowsCollector(session=mock_session, browser=mock_browser)
        html = collector._get_html("https://www.etf.com/SPY#702")

        assert html == SAMPLE_FUND_FLOWS_HTML
        mock_session.get_with_retry.assert_called_once()


# =============================================================================
# FundFlowsCollector fetch() tests
# =============================================================================


class TestFundFlowsFetch:
    """FundFlowsCollector.fetch() のテスト。"""

    def test_正常系_DataFrameを返却する(self) -> None:
        """fetch() が pd.DataFrame を返却すること。"""
        from market.etfcom.collectors import FundFlowsCollector

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_FUND_FLOWS_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundFlowsCollector(session=mock_session, config=config)

        df = collector.fetch(ticker="SPY")

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "date" in df.columns
        assert "ticker" in df.columns
        assert "net_flows" in df.columns

    def test_正常系_FUND_FLOWS_URL_TEMPLATEを使用する(self) -> None:
        """fetch() が FUND_FLOWS_URL_TEMPLATE を使用して URL を構築すること。"""
        from market.etfcom.collectors import FundFlowsCollector
        from market.etfcom.constants import FUND_FLOWS_URL_TEMPLATE

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_FUND_FLOWS_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundFlowsCollector(session=mock_session, config=config)

        collector.fetch(ticker="SPY")

        # Verify the URL was constructed using the template
        called_url = mock_session.get_with_retry.call_args[0][0]
        expected_url = FUND_FLOWS_URL_TEMPLATE.format(ticker="SPY")
        assert called_url == expected_url


# =============================================================================
# FundFlowsCollector validate() tests
# =============================================================================


class TestFundFlowsValidate:
    """FundFlowsCollector.validate() のテスト。"""

    def test_正常系_必須カラムが存在してTrue(self) -> None:
        """必須カラムが全て存在する DataFrame で True を返すこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        df = pd.DataFrame(
            {
                "date": ["2025-09-10"],
                "ticker": ["SPY"],
                "net_flows": [2787.59],
            }
        )

        assert collector.validate(df) is True

    def test_異常系_空DataFrameでFalse(self) -> None:
        """空 DataFrame で False を返すこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        df = pd.DataFrame()

        assert collector.validate(df) is False

    def test_異常系_必須カラムなしでFalse(self) -> None:
        """必須カラムがない DataFrame で False を返すこと。"""
        from market.etfcom.collectors import FundFlowsCollector

        collector = FundFlowsCollector()
        df = pd.DataFrame({"some_column": [1, 2, 3]})

        assert collector.validate(df) is False


# =============================================================================
# Ticker normalization tests
# =============================================================================


class TestTickerNormalization:
    """3 つの Collector のティッカー大文字正規化テスト。"""

    def test_正常系_FundamentalsCollectorが小文字を大文字に正規化する(self) -> None:
        """FundamentalsCollector.fetch() が小文字ティッカーを大文字に正規化すること。"""
        from market.etfcom.collectors import FundamentalsCollector
        from market.etfcom.constants import PROFILE_URL_TEMPLATE

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_PROFILE_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["spy"])

        # URL should use uppercase ticker
        called_url = mock_session.get_with_retry.call_args[0][0]
        expected_url = PROFILE_URL_TEMPLATE.format(ticker="SPY")
        assert called_url == expected_url

        # DataFrame ticker should be uppercase
        assert df["ticker"].iloc[0] == "SPY"

    def test_正常系_FundamentalsCollectorが大文字入力でも正常動作する(self) -> None:
        """FundamentalsCollector.fetch() が大文字入力でも冪等に動作すること。"""
        from market.etfcom.collectors import FundamentalsCollector
        from market.etfcom.constants import PROFILE_URL_TEMPLATE

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_PROFILE_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["SPY"])

        called_url = mock_session.get_with_retry.call_args[0][0]
        expected_url = PROFILE_URL_TEMPLATE.format(ticker="SPY")
        assert called_url == expected_url
        assert df["ticker"].iloc[0] == "SPY"

    def test_正常系_FundFlowsCollectorが小文字を大文字に正規化する(self) -> None:
        """FundFlowsCollector.fetch() が小文字ティッカーを大文字に正規化すること。"""
        from market.etfcom.collectors import FundFlowsCollector
        from market.etfcom.constants import FUND_FLOWS_URL_TEMPLATE

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = SAMPLE_FUND_FLOWS_HTML
        mock_response.status_code = 200
        mock_session.get_with_retry.return_value = mock_response

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundFlowsCollector(session=mock_session, config=config)

        df = collector.fetch(ticker="spy")

        # URL should use uppercase ticker
        called_url = mock_session.get_with_retry.call_args[0][0]
        expected_url = FUND_FLOWS_URL_TEMPLATE.format(ticker="SPY")
        assert called_url == expected_url

        # DataFrame ticker should be uppercase
        assert df["ticker"].iloc[0] == "SPY"

    def test_正常系_HistoricalFundFlowsCollectorが小文字を大文字に正規化する(
        self,
    ) -> None:
        """HistoricalFundFlowsCollector.fetch() が小文字ティッカーを大文字に正規化すること。"""
        from market.etfcom.collectors import HistoricalFundFlowsCollector

        mock_session = MagicMock()
        collector = HistoricalFundFlowsCollector(session=mock_session)

        # Mock _resolve_fund_id and _fetch_fund_flows to avoid actual API calls
        with (
            patch.object(
                collector, "_resolve_fund_id", return_value=12345
            ) as mock_resolve,
            patch.object(collector, "_fetch_fund_flows", return_value=[]),
        ):
            collector.fetch(ticker="spy")

        # _resolve_fund_id should be called with uppercase ticker
        mock_resolve.assert_called_once_with("SPY")


# =============================================================================
# FundamentalsCollector ETFComNotFoundError handling tests
# =============================================================================


class TestFundamentalsNotFoundHandling:
    """FundamentalsCollector.fetch() の ETFComNotFoundError ハンドリングテスト。"""

    def test_正常系_404エラー時にminimalレコードが追加される(self) -> None:
        """ETFComNotFoundError 発生時に最小レコード {"ticker": ticker} が追加されること。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        # First ticker succeeds, second raises ETFComNotFoundError
        mock_response_ok = MagicMock()
        mock_response_ok.text = SAMPLE_PROFILE_HTML
        mock_response_ok.status_code = 200

        mock_session.get_with_retry.side_effect = [
            mock_response_ok,
            ETFComNotFoundError(
                "ETF not found: HTTP 404",
                url="https://www.etf.com/INVALID",
            ),
        ]

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["SPY", "INVALID"])

        # Both tickers should be in the result
        assert len(df) == 2
        assert df["ticker"].tolist() == ["SPY", "INVALID"]

    def test_正常系_404エラー後も他ティッカーの処理が継続される(self) -> None:
        """ETFComNotFoundError 後も残りのティッカーの処理が継続されること。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_response_ok = MagicMock()
        mock_response_ok.text = SAMPLE_PROFILE_HTML
        mock_response_ok.status_code = 200

        # First raises 404, second succeeds
        mock_session.get_with_retry.side_effect = [
            ETFComNotFoundError(
                "ETF not found: HTTP 404",
                url="https://www.etf.com/INVALID",
            ),
            mock_response_ok,
        ]

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        df = collector.fetch(tickers=["INVALID", "SPY"])

        assert len(df) == 2
        # INVALID should have minimal record, SPY should have full data
        invalid_row = df[df["ticker"] == "INVALID"].iloc[0]
        spy_row = df[df["ticker"] == "SPY"].iloc[0]

        # INVALID should only have ticker field (other fields NaN)
        assert pd.isna(invalid_row.get("issuer"))
        # SPY should have full data
        assert spy_row["issuer"] == "State Street"

    def test_正常系_404時にPlaywrightフォールバックがトリガーされない(self) -> None:
        """ETFComNotFoundError が _get_html() から直接伝播し Playwright fallback しないこと。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        mock_session.get_with_retry.side_effect = ETFComNotFoundError(
            "ETF not found: HTTP 404",
            url="https://www.etf.com/INVALID",
        )

        mock_browser = AsyncMock()

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(
            session=mock_session, browser=mock_browser, config=config
        )

        df = collector.fetch(tickers=["INVALID"])

        # Browser should NOT be called (no Playwright fallback for 404)
        mock_browser._get_page_html_with_retry.assert_not_called()
        # Should still get a minimal record
        assert len(df) == 1
        assert df["ticker"].iloc[0] == "INVALID"


# =============================================================================
# Ticker Validation
# =============================================================================


class TestTickerValidation:
    """_normalize_ticker() のバリデーションテスト。"""

    def test_異常系_不正なティッカーでValueError(self) -> None:
        """パストラバーサルやインジェクション文字列で ValueError が送出されること。"""
        from market.etfcom.collectors import _normalize_ticker

        invalid_tickers = [
            "../etc",
            "SPY?admin=true",
            "A" * 11,  # 11 chars exceeds 10-char limit
            "SPY FOO",  # space
            "",  # empty after strip
            "  ",  # whitespace only
            "SPY@COM",  # @ symbol
        ]
        for ticker in invalid_tickers:
            with pytest.raises(ValueError, match="Invalid ticker symbol"):
                _normalize_ticker(ticker)

    def test_正常系_ハイフン付きティッカーで正常動作(self) -> None:
        """ハイフン付きティッカー（例: BRK-B）が正常に正規化されること。"""
        from market.etfcom.collectors import _normalize_ticker

        assert _normalize_ticker("BRK-B") == "BRK-B"
        assert _normalize_ticker("brk-b") == "BRK-B"

    def test_正常系_通常のティッカーで正常動作(self) -> None:
        """通常のティッカーシンボルが正常に正規化されること。"""
        from market.etfcom.collectors import _normalize_ticker

        assert _normalize_ticker("spy") == "SPY"
        assert _normalize_ticker("  VOO  ") == "VOO"
        assert _normalize_ticker("QQQ") == "QQQ"

    def test_異常系_FundamentalsCollectorで不正ティッカーがValueError(self) -> None:
        """FundamentalsCollector.fetch() が不正ティッカーで ValueError を送出すること。"""
        from market.etfcom.collectors import FundamentalsCollector

        mock_session = MagicMock()
        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundamentalsCollector(session=mock_session, config=config)

        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            collector.fetch(tickers=["../etc"])

    def test_異常系_FundFlowsCollectorで不正ティッカーがValueError(self) -> None:
        """FundFlowsCollector.fetch() が不正ティッカーで ValueError を送出すること。"""
        from market.etfcom.collectors import FundFlowsCollector

        mock_session = MagicMock()
        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundFlowsCollector(session=mock_session, config=config)

        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            collector.fetch(ticker="SPY?admin=true")


# =============================================================================
# FundFlows NotFound Handling
# =============================================================================


class TestFundFlowsNotFoundHandling:
    """FundFlowsCollector.fetch() の ETFComNotFoundError ハンドリングテスト。"""

    def test_異常系_404エラーが呼び出し元に伝播する(self) -> None:
        """ETFComNotFoundError が FundFlowsCollector.fetch() から伝播すること。"""
        from market.etfcom.collectors import FundFlowsCollector

        mock_session = MagicMock()
        mock_session.get_with_retry.side_effect = ETFComNotFoundError(
            "ETF not found: HTTP 404",
            url="https://www.etf.com/etfflows/INVALID",
        )

        config = ScrapingConfig(polite_delay=0.0, delay_jitter=0.0)
        collector = FundFlowsCollector(session=mock_session, config=config)

        with pytest.raises(ETFComNotFoundError):
            collector.fetch(ticker="INVALID")
