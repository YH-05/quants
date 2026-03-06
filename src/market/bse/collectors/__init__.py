"""BSE data collector implementations.

This subpackage contains collector classes for various BSE data
endpoints (e.g., scrip quotes, bhavcopy, corporate actions).

Public API
----------
QuoteCollector
    Collector for BSE scrip quote and historical price data.
"""

from market.bse.collectors.quote import QuoteCollector

__all__ = ["QuoteCollector"]
