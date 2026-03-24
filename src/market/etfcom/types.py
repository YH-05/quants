"""Type definitions for the market.etfcom module.

This module provides dataclass definitions for ETF.com data retrieval including:

- Scraping configuration (bot-blocking countermeasures)
- Retry configuration (exponential backoff)
- API authentication configuration (OAuth token, API keys)
- REST API record types (ticker info)

All configuration dataclasses use ``frozen=True`` to ensure immutability.
Field names use snake_case following project convention; raw ETF.com column
names (e.g. "Expense Ratio") are mapped to snake_case during parsing.

See Also
--------
market.etfcom.constants : Default values referenced by ScrapingConfig.
market.yfinance.types : Similar type-definition pattern for yfinance module.
market.fred.types : Similar type-definition pattern for FRED module.
"""

from dataclasses import dataclass, field
from datetime import datetime

from market.etfcom.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class ScrapingConfig:
    """Configuration for ETF.com scraping behaviour.

    Controls polite delays, TLS fingerprint impersonation, Playwright
    headless mode, and page-level retry settings.  Default values are
    sourced from ``market.etfcom.constants`` to keep a single source of
    truth.

    Parameters
    ----------
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 2.0).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 1.0).
    user_agents : tuple[str, ...]
        User-Agent strings for HTTP request rotation.  When empty the
        default list from ``constants.DEFAULT_USER_AGENTS`` is used at
        runtime (default: ``()``).
    impersonate : str
        curl_cffi TLS fingerprint impersonation target
        (default: ``'chrome'``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    headless : bool
        Whether to run Playwright in headless mode (default: True).
    stability_wait : float
        Wait time in seconds for page stability after navigation
        (default: ``DEFAULT_STABILITY_WAIT`` = 1.0).
    max_page_retries : int
        Maximum number of page-level retries for scraping operations
        (default: 5).

    Examples
    --------
    >>> config = ScrapingConfig(polite_delay=3.0, headless=False)
    >>> config.polite_delay
    3.0
    """

    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER
    user_agents: tuple[str, ...] = ()
    impersonate: str = "chrome"
    timeout: float = DEFAULT_TIMEOUT
    headless: bool = True
    stability_wait: float = 2.0  # seconds; empirical minimum for JS-heavy ETF pages
    max_page_retries: int = 5


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    initial_delay : float
        Initial delay between retries in seconds (default: 1.0).
    max_delay : float
        Maximum delay between retries in seconds (default: 30.0).
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0).
    jitter : bool
        Whether to add random jitter to delays (default: True).

    Examples
    --------
    >>> config = RetryConfig(max_attempts=5, initial_delay=0.5)
    >>> config.max_attempts
    5
    """

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


# =============================================================================
# API Authentication Dataclass
# =============================================================================


@dataclass(frozen=True)
class AuthConfig:
    """API authentication credentials from the ETF.com ``/api/v1/api-details`` endpoint.

    Stores the 6 fields returned by the authentication endpoint plus a
    ``fetched_at`` timestamp for cache TTL validation against
    ``constants.AUTH_TOKEN_TTL_SECONDS``.

    Sensitive fields (``fund_api_key``, ``tools_api_key``, ``oauth_token``)
    are excluded from ``repr`` output to prevent accidental exposure in
    logs (CWE-532).

    Parameters
    ----------
    api_base_url : str
        Base URL for the ETF.com REST API
        (e.g. ``"https://api-prod.etf.com"``).
    fund_api_key : str
        API key for fund data endpoints. Excluded from ``repr``.
    tools_api_key : str
        API key for tools endpoints. Excluded from ``repr``.
    oauth_token : str
        OAuth Bearer token for ``/v2/`` API requests (24h TTL).
        Excluded from ``repr``.
    real_time_api_url : str
        URL for the real-time GraphQL API
        (e.g. ``"https://real-time-prod.etf.com/graphql"``).
    graphql_api_url : str
        URL for the GraphQL data API
        (e.g. ``"https://data.etf.com"``).
    fetched_at : datetime
        UTC timestamp when the credentials were fetched, used to
        determine token expiry against ``AUTH_TOKEN_TTL_SECONDS``.

    Examples
    --------
    >>> from datetime import datetime, timezone
    >>> auth = AuthConfig(
    ...     api_base_url="https://api-prod.etf.com",
    ...     fund_api_key="fund-key",
    ...     tools_api_key="tools-key",
    ...     oauth_token="token",
    ...     real_time_api_url="https://real-time-prod.etf.com/graphql",
    ...     graphql_api_url="https://data.etf.com",
    ...     fetched_at=datetime.now(tz=timezone.utc),
    ... )
    >>> auth.api_base_url
    'https://api-prod.etf.com'
    >>> "fund-key" not in repr(auth)  # sensitive fields hidden
    True

    See Also
    --------
    market.etfcom.constants.AUTH_DETAILS_URL : Endpoint that returns these credentials.
    market.etfcom.constants.AUTH_TOKEN_TTL_SECONDS : TTL for oauth_token validity.
    """

    api_base_url: str
    fund_api_key: str = field(repr=False)
    tools_api_key: str = field(repr=False)
    oauth_token: str = field(repr=False)
    real_time_api_url: str
    graphql_api_url: str
    fetched_at: datetime


# =============================================================================
# REST API Data Record Dataclasses
# =============================================================================


@dataclass(frozen=True)
class TickerInfo:
    """Ticker information from the ETF.com tickers API endpoint.

    Contains the 6 fields returned by the ``tickers`` API endpoint for
    each ETF. Used primarily to resolve ticker symbols to fund IDs
    required by the ``fund-flows-query`` endpoint.

    Parameters
    ----------
    ticker : str
        ETF ticker symbol (e.g. ``"SPY"``).
    fund_id : int
        Unique fund identifier used by the ETF.com API.
    name : str
        Full fund name (e.g. ``"SPDR S&P 500 ETF Trust"``).
    issuer : str | None
        Fund issuer name (e.g. ``"State Street"``).
    asset_class : str | None
        Asset class (e.g. ``"Equity"``, ``"Fixed Income"``).
    inception_date : str | None
        Fund inception date as returned by the API (e.g. ``"1993-01-22"``).

    Examples
    --------
    >>> info = TickerInfo(
    ...     ticker="SPY",
    ...     fund_id=1,
    ...     name="SPDR S&P 500 ETF Trust",
    ...     issuer="State Street",
    ...     asset_class="Equity",
    ...     inception_date="1993-01-22",
    ... )
    >>> info.fund_id
    1
    """

    ticker: str
    fund_id: int
    name: str
    issuer: str | None
    asset_class: str | None
    inception_date: str | None


# =============================================================================
# Module exports
# =============================================================================

__all__ = [
    "AuthConfig",
    "RetryConfig",
    "ScrapingConfig",
    "TickerInfo",
]
