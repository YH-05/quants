"""Portfolio return calculator with corporate action handling.

Calculates daily weighted portfolio returns and benchmark returns,
handling corporate actions (delisting/merger) by setting affected
ticker weights to zero and redistributing proportionally to remaining
tickers.

The calculator relies on a ``PriceDataProvider`` Protocol for fetching
daily close prices, making it agnostic to the underlying data source
(yfinance, Bloomberg, FactSet, or test stubs).

Examples
--------
>>> from dev.ca_strategy.return_calculator import PortfolioReturnCalculator
>>> calc = PortfolioReturnCalculator(
...     price_provider=my_provider,
...     corporate_actions=actions_list,
... )
>>> portfolio_returns = calc.calculate_returns(
...     weights={"AAPL": 0.5, "MSFT": 0.3, "GOOGL": 0.2},
...     start=date(2016, 1, 1),
...     end=date(2026, 2, 28),
... )
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

import pandas as pd

from utils_core.logging import get_logger

if TYPE_CHECKING:
    from dev.ca_strategy.price_provider import PriceDataProvider

logger = get_logger(__name__)

__all__ = ["PortfolioReturnCalculator"]


class PortfolioReturnCalculator:
    """Calculate daily weighted portfolio returns with corporate action handling.

    Parameters
    ----------
    price_provider : PriceDataProvider
        Provider for fetching daily close prices.
    corporate_actions : list[dict[str, Any]]
        List of corporate action records, each containing at minimum:
        ``ticker``, ``action_date`` (ISO 8601 string), and ``action_type``
        (``"delisting"`` or ``"merger"``).

    Examples
    --------
    >>> calc = PortfolioReturnCalculator(
    ...     price_provider=provider,
    ...     corporate_actions=[
    ...         {"ticker": "EMC", "action_date": "2016-09-07",
    ...          "action_type": "delisting", "company_name": "EMC Corp",
    ...          "reason": "Merged into Dell Technologies"},
    ...     ],
    ... )
    """

    def __init__(
        self,
        price_provider: PriceDataProvider,
        corporate_actions: list[dict[str, Any]],
    ) -> None:
        self._price_provider = price_provider
        self._corporate_actions = self._parse_actions(corporate_actions)
        logger.debug(
            "PortfolioReturnCalculator initialized",
            corporate_action_count=len(self._corporate_actions),
        )

    def calculate_returns(
        self,
        weights: dict[str, float],
        start: date,
        end: date,
    ) -> pd.Series:
        """Calculate daily portfolio returns.

        Algorithm
        ---------
        1. Fetch daily close prices for all tickers via PriceDataProvider.
        2. Compute daily returns from price changes.
        3. For each trading day:
           a. Check corporate_actions for delisting/merger on this date.
           b. If action found: set weight to 0, redistribute proportionally.
           c. Compute weighted daily return = sum(weight_i * return_i).
        4. Return pd.Series of daily returns.

        Parameters
        ----------
        weights : dict[str, float]
            Initial portfolio weights keyed by ticker.
        start : date
            Start date (inclusive) for price data.
        end : date
            End date (inclusive) for price data.

        Returns
        -------
        pd.Series
            Daily weighted portfolio returns with DatetimeIndex.
            Empty Series if no price data is available.
        """
        tickers = list(weights.keys())

        logger.info(
            "Calculating portfolio returns",
            ticker_count=len(tickers),
            start=start.isoformat(),
            end=end.isoformat(),
        )

        prepared = self._fetch_and_prepare_returns(tickers, start, end)
        if prepared is None:
            return pd.Series([], dtype=float)

        returns_df, missing_tickers = prepared

        # Adjust initial weights for missing tickers
        current_weights = self._redistribute_weights(
            current_weights=weights,
            removed_tickers=missing_tickers,
        )

        # Calculate weighted daily returns with corporate action handling
        daily_returns = self._compute_weighted_returns(
            returns_df=returns_df,
            initial_weights=current_weights,
        )

        logger.info(
            "Portfolio returns calculated",
            return_count=len(daily_returns),
        )

        return daily_returns

    def calculate_benchmark_returns(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> pd.Series:
        """Calculate equal-weight benchmark returns for all universe tickers.

        Uses equal weight (1/N) for all tickers with available data.
        Corporate actions are applied to the benchmark as well.

        Parameters
        ----------
        tickers : list[str]
            List of ticker symbols in the universe.
        start : date
            Start date (inclusive).
        end : date
            End date (inclusive).

        Returns
        -------
        pd.Series
            Daily equal-weight benchmark returns with DatetimeIndex.
            Empty Series if no price data is available.
        """
        if not tickers:
            logger.warning("Empty tickers list for benchmark calculation")
            return pd.Series([], dtype=float)

        logger.info(
            "Calculating benchmark returns",
            ticker_count=len(tickers),
            start=start.isoformat(),
            end=end.isoformat(),
        )

        prepared = self._fetch_and_prepare_returns(tickers, start, end)
        if prepared is None:
            return pd.Series([], dtype=float)

        returns_df, _ = prepared

        # Equal weights for available tickers
        n = len(returns_df.columns)
        equal_weight = 1.0 / n
        weights = {ticker: equal_weight for ticker in returns_df.columns}

        # Compute weighted returns (with corporate action handling)
        daily_returns = self._compute_weighted_returns(
            returns_df=returns_df,
            initial_weights=weights,
        )

        logger.info(
            "Benchmark returns calculated",
            return_count=len(daily_returns),
        )

        return daily_returns

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------
    def _fetch_and_prepare_returns(
        self,
        tickers: list[str],
        start: date,
        end: date,
    ) -> tuple[pd.DataFrame, set[str]] | None:
        """Fetch prices and build daily returns DataFrame.

        Common pipeline shared by :meth:`calculate_returns` and
        :meth:`calculate_benchmark_returns` to avoid code duplication.

        Parameters
        ----------
        tickers : list[str]
            Ticker symbols to fetch.
        start : date
            Start date (inclusive).
        end : date
            End date (inclusive).

        Returns
        -------
        tuple[pd.DataFrame, set[str]] | None
            ``(returns_df, missing_tickers)`` if data is available,
            ``None`` if no price data or empty returns.
        """
        price_data = self._price_provider.fetch(tickers, start, end)

        if not price_data:
            logger.warning("No price data returned from provider")
            return None

        available_tickers = set(price_data.keys())
        missing_tickers = set(tickers) - available_tickers

        if missing_tickers:
            logger.warning(
                "Data missing for tickers, excluding from calculation",
                missing_tickers=sorted(missing_tickers),
            )

        returns_df = self._build_returns_df(price_data)

        if returns_df.empty:
            logger.warning("Returns DataFrame is empty after computing daily returns")
            return None

        return returns_df, missing_tickers

    def _parse_actions(
        self,
        actions: list[dict[str, Any]],
    ) -> dict[str, date]:
        """Parse corporate actions into a ticker -> action_date mapping.

        Invalid entries (missing fields, bad date format) are skipped
        with a warning log rather than raising an exception.

        Parameters
        ----------
        actions : list[dict[str, Any]]
            Raw corporate action records.

        Returns
        -------
        dict[str, date]
            Mapping of ticker to action date.
        """
        result: dict[str, date] = {}
        for i, action in enumerate(actions):
            try:
                ticker = action["ticker"]
                action_date = date.fromisoformat(action["action_date"])
            except KeyError as e:
                logger.warning(
                    "Skipping corporate action with missing field",
                    index=i,
                    missing_field=str(e),
                )
                continue
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Skipping corporate action with invalid date",
                    index=i,
                    error=str(e),
                )
                continue

            result[ticker] = action_date
            logger.debug(
                "Corporate action parsed",
                ticker=ticker,
                action_date=action_date.isoformat(),
                action_type=action.get("action_type", "unknown"),
            )
        return result

    def _build_returns_df(
        self,
        price_data: dict[str, pd.Series],
    ) -> pd.DataFrame:
        """Build a DataFrame of daily returns from price data.

        Parameters
        ----------
        price_data : dict[str, pd.Series]
            Mapping of ticker to daily close price Series.

        Returns
        -------
        pd.DataFrame
            Daily returns DataFrame with tickers as columns and
            DatetimeIndex as index.
        """
        prices_df = pd.DataFrame(price_data)
        returns_df = prices_df.pct_change().iloc[1:]
        return returns_df

    def _redistribute_weights(
        self,
        current_weights: dict[str, float],
        removed_tickers: set[str],
    ) -> dict[str, float]:
        """Redistribute weights from removed tickers proportionally.

        Sets removed tickers' weights to 0 and redistributes their
        combined weight proportionally to remaining tickers so that
        the total weight remains 1.0.

        Parameters
        ----------
        current_weights : dict[str, float]
            Current weight mapping.
        removed_tickers : set[str]
            Set of tickers to remove.

        Returns
        -------
        dict[str, float]
            New weights with removed tickers excluded and remaining
            weights scaled to sum to 1.0.
        """
        if not removed_tickers:
            return dict(current_weights)

        remaining = {
            k: v for k, v in current_weights.items() if k not in removed_tickers
        }

        if not remaining:
            logger.warning(
                "All tickers removed, no remaining weights to redistribute",
                removed_count=len(removed_tickers),
            )
            return {}

        remaining_total = sum(remaining.values())
        if remaining_total == 0:
            logger.warning("Remaining weights sum to 0, cannot redistribute")
            return remaining

        # Scale remaining weights to sum to 1.0
        new_weights = {k: v / remaining_total for k, v in remaining.items()}

        logger.info(
            "Weights redistributed",
            removed_tickers=sorted(removed_tickers),
            new_weight_count=len(new_weights),
        )

        return new_weights

    def _compute_weighted_returns(
        self,
        returns_df: pd.DataFrame,
        initial_weights: dict[str, float],
    ) -> pd.Series:
        """Compute weighted daily returns with corporate action handling.

        For each trading day, checks whether any corporate action occurs
        on that date. If so, the affected ticker's weight is set to 0
        and the freed weight is redistributed proportionally to remaining
        tickers.

        Uses vectorized pandas operations for the daily return computation
        (element-wise multiply + row sum) while iterating over dates only
        for corporate action state tracking.

        Parameters
        ----------
        returns_df : pd.DataFrame
            Daily returns with tickers as columns.
        initial_weights : dict[str, float]
            Starting weights (already adjusted for missing data).

        Returns
        -------
        pd.Series
            Weighted daily portfolio returns.
        """
        # Only use tickers present in returns_df
        active_tickers = set(returns_df.columns) & set(initial_weights.keys())
        current_weights = {t: initial_weights[t] for t in active_tickers}

        # Normalize if needed (tickers might have been dropped)
        total = sum(current_weights.values())
        if total > 0 and abs(total - 1.0) > 1e-10:
            current_weights = {k: v / total for k, v in current_weights.items()}

        # Build weight matrix row-by-row (corporate actions change weights)
        weight_rows: list[dict[str, float]] = []

        for idx_date in returns_df.index:
            # Check for corporate actions on this date
            trading_date = idx_date.date() if hasattr(idx_date, "date") else idx_date
            removed_on_date: set[str] = set()

            for ticker, action_date in self._corporate_actions.items():
                if ticker in current_weights and trading_date >= action_date:
                    removed_on_date.add(ticker)

            if removed_on_date:
                current_weights = self._redistribute_weights(
                    current_weights=current_weights,
                    removed_tickers=removed_on_date,
                )
                logger.info(
                    "Corporate action applied on date",
                    date=str(trading_date),
                    removed_tickers=sorted(removed_on_date),
                )

            weight_rows.append(dict(current_weights))

        # Vectorized computation: build weights DataFrame, align columns,
        # element-wise multiply, and sum across tickers per day
        weights_df = pd.DataFrame(weight_rows, index=returns_df.index)
        weights_df = weights_df.reindex(columns=returns_df.columns, fill_value=0.0)

        return (returns_df.fillna(0.0) * weights_df).sum(axis=1)
