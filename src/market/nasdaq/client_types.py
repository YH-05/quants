"""Type definitions for the NasdaqClient module.

This module provides fetch option types for the NasdaqClient,
controlling cache behaviour on a per-request basis.

The ``NasdaqFetchOptions`` dataclass mirrors
``market.alphavantage.types.FetchOptions`` for API consistency.

See Also
--------
market.alphavantage.types.FetchOptions : Reference implementation.
market.nasdaq.client : NasdaqClient that consumes these options.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class NasdaqFetchOptions:
    """Options for NasdaqClient fetch requests.

    Controls whether cached data is used and whether to force a fresh
    fetch from the NASDAQ API, ignoring any cached response.

    Parameters
    ----------
    use_cache : bool
        Whether to use cached data if available (default: True).
    force_refresh : bool
        Whether to force a fresh fetch, ignoring cache (default: False).

    Examples
    --------
    >>> options = NasdaqFetchOptions()
    >>> options.use_cache
    True
    >>> options.force_refresh
    False

    >>> NasdaqFetchOptions(use_cache=False)
    NasdaqFetchOptions(use_cache=False, force_refresh=False)
    """

    use_cache: bool = True
    force_refresh: bool = False


__all__ = ["NasdaqFetchOptions"]
