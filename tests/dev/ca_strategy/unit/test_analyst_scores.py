"""Tests for load_analyst_scores function.

load_analyst_scores reads list_portfolio_20151224.json and universe.json,
extracts KY/AK analyst scores, and maps them to CA Strategy tickers.

Key behaviors:
- Maps Bloomberg_Ticker from portfolio list to CA Strategy ticker via universe
- KY/AK values of " " (space) are treated as None
- Only tickers with at least one valid score are included
- Bloomberg_Ticker that is null or not in universe is skipped
- Returns dict[str, AnalystScore]
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from dev.ca_strategy.analyst_scores import load_analyst_scores
from dev.ca_strategy.types import AnalystScore


def _write_json(path: Path, data: object) -> None:
    """Write data as JSON to path."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _make_universe(tickers: list[dict[str, str]]) -> dict[str, object]:
    """Create a universe.json structure."""
    return {
        "_metadata": {"total_count": len(tickers)},
        "tickers": [
            {
                "ticker": t["ticker"],
                "bloomberg_ticker": t["bloomberg_ticker"],
                "company_name": t.get("company_name", "Test Corp"),
                "gics_sector": t.get("gics_sector", "Information Technology"),
                "country": t.get("country", "US"),
            }
            for t in tickers
        ],
    }


def _make_portfolio(
    entries: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Create a list_portfolio JSON structure.

    Each entry should have: msci_id, Bloomberg_Ticker, KY, AK.
    """
    result: dict[str, list[dict[str, object]]] = {}
    for entry in entries:
        msci_id = str(entry["msci_id"])
        record = {
            "Name": entry.get("Name", "Test Company"),
            "Country": entry.get("Country", "US"),
            "GICS_Sector": entry.get("GICS_Sector", "Information Technology"),
            "GICS_Industry": entry.get("GICS_Industry", "Software"),
            "MSCI_Mkt_Cap_USD_MM": 10000.0,
            "KY": entry.get("KY", " "),
            "AK": entry.get("AK", " "),
            "Total": entry.get("Total", " "),
            "Target_Weight": " ",
            "LIST": "LIST",
            "date": "2015-12-24T00:00:00.000",
            "Bloomberg_Ticker": entry.get("Bloomberg_Ticker"),
            "FIGI": "BBG000TEST00",
        }
        result[msci_id] = [record]
    return result


class TestLoadAnalystScores:
    """load_analyst_scores unit tests."""

    def test_正常系_KY_AK両方ある銘柄の読み取り(self, tmp_path: Path) -> None:
        """Ticker with both KY and AK should be included with both values."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe([{"ticker": "AAPL", "bloomberg_ticker": "AAPL US Equity"}]),
        )
        _write_json(
            portfolio_path,
            _make_portfolio(
                [
                    {
                        "msci_id": "001",
                        "Bloomberg_Ticker": "AAPL US Equity",
                        "KY": 2,
                        "AK": 3,
                    }
                ]
            ),
        )

        result = load_analyst_scores(portfolio_path, universe_path)

        assert "AAPL" in result
        assert result["AAPL"].ticker == "AAPL"
        assert result["AAPL"].ky == 2
        assert result["AAPL"].ak == 3

    def test_正常系_KYのみある銘柄(self, tmp_path: Path) -> None:
        """Ticker with only KY (AK is space) should have ak=None."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe([{"ticker": "MSFT", "bloomberg_ticker": "MSFT US Equity"}]),
        )
        _write_json(
            portfolio_path,
            _make_portfolio(
                [
                    {
                        "msci_id": "002",
                        "Bloomberg_Ticker": "MSFT US Equity",
                        "KY": 1,
                        "AK": " ",
                    }
                ]
            ),
        )

        result = load_analyst_scores(portfolio_path, universe_path)

        assert "MSFT" in result
        assert result["MSFT"].ky == 1
        assert result["MSFT"].ak is None

    def test_正常系_スコアなし銘柄は除外(self, tmp_path: Path) -> None:
        """Ticker where both KY and AK are space should be excluded."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe(
                [{"ticker": "GOOGL", "bloomberg_ticker": "GOOGL US Equity"}]
            ),
        )
        _write_json(
            portfolio_path,
            _make_portfolio(
                [
                    {
                        "msci_id": "003",
                        "Bloomberg_Ticker": "GOOGL US Equity",
                        "KY": " ",
                        "AK": " ",
                    }
                ]
            ),
        )

        result = load_analyst_scores(portfolio_path, universe_path)

        assert "GOOGL" not in result
        assert len(result) == 0

    def test_正常系_Bloomberg_Tickerがnullの銘柄はスキップ(
        self, tmp_path: Path
    ) -> None:
        """Entry with Bloomberg_Ticker=null should be skipped."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe([{"ticker": "AAPL", "bloomberg_ticker": "AAPL US Equity"}]),
        )
        _write_json(
            portfolio_path,
            _make_portfolio(
                [
                    {
                        "msci_id": "004",
                        "Bloomberg_Ticker": None,
                        "KY": 2,
                        "AK": 3,
                    }
                ]
            ),
        )

        result = load_analyst_scores(portfolio_path, universe_path)
        assert len(result) == 0

    def test_正常系_universeに存在しないBloomberg_Tickerはスキップ(
        self, tmp_path: Path
    ) -> None:
        """Entry with Bloomberg_Ticker not in universe mapping should be skipped."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe([{"ticker": "AAPL", "bloomberg_ticker": "AAPL US Equity"}]),
        )
        _write_json(
            portfolio_path,
            _make_portfolio(
                [
                    {
                        "msci_id": "005",
                        "Bloomberg_Ticker": "UNKNOWN US Equity",
                        "KY": 2,
                        "AK": 3,
                    }
                ]
            ),
        )

        result = load_analyst_scores(portfolio_path, universe_path)
        assert len(result) == 0

    def test_エッジケース_空のportfolioリスト(self, tmp_path: Path) -> None:
        """Empty portfolio list should return empty dict."""
        universe_path = tmp_path / "universe.json"
        portfolio_path = tmp_path / "portfolio.json"

        _write_json(
            universe_path,
            _make_universe([{"ticker": "AAPL", "bloomberg_ticker": "AAPL US Equity"}]),
        )
        _write_json(portfolio_path, {})

        result = load_analyst_scores(portfolio_path, universe_path)
        assert result == {}
