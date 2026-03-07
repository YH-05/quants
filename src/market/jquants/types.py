"""Type definitions for the market.jquants module.

This module provides type definitions for J-Quants API data retrieval including:

- Configuration dataclasses (JQuantsConfig, RetryConfig, FetchOptions)
- Token management dataclass (TokenInfo)

All dataclasses use ``frozen=True`` to ensure immutability where appropriate.

See Also
--------
market.bse.types : Similar type-definition pattern for the BSE module.
market.jquants.constants : Default values referenced by JQuantsConfig.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from market.jquants.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
    TOKEN_FILE_PATH,
)

# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass(frozen=True)
class JQuantsConfig:
    """Configuration for J-Quants API client.

    Controls authentication credentials, HTTP behaviour, polite delays,
    and token persistence path.

    Parameters
    ----------
    mail_address : str
        J-Quants login email address. If empty, read from
        ``JQUANTS_MAIL_ADDRESS`` environment variable at runtime.
    password : str
        J-Quants login password. If empty, read from
        ``JQUANTS_PASSWORD`` environment variable at runtime.
    token_file_path : str
        Path to token persistence file
        (default: ``TOKEN_FILE_PATH`` = ``~/.jquants/token.json``).
    timeout : float
        HTTP request timeout in seconds
        (default: ``DEFAULT_TIMEOUT`` = 30.0).
    polite_delay : float
        Minimum wait time between consecutive requests in seconds
        (default: ``DEFAULT_POLITE_DELAY`` = 0.1).
    delay_jitter : float
        Random jitter added to polite delay in seconds
        (default: ``DEFAULT_DELAY_JITTER`` = 0.05).

    Raises
    ------
    ValueError
        If any configuration value is outside its valid range.

    Examples
    --------
    >>> config = JQuantsConfig(
    ...     mail_address="user@example.com",
    ...     password="secret",
    ... )
    >>> config.timeout
    30.0
    """

    mail_address: str = ""
    password: str = field(default="", repr=False)
    token_file_path: str = TOKEN_FILE_PATH
    timeout: float = DEFAULT_TIMEOUT
    polite_delay: float = DEFAULT_POLITE_DELAY
    delay_jitter: float = DEFAULT_DELAY_JITTER

    def __post_init__(self) -> None:
        """Validate configuration value ranges.

        Raises
        ------
        ValueError
            If any configuration value is outside its valid range.
        """
        if not (1.0 <= self.timeout <= 300.0):
            raise ValueError(
                f"timeout must be between 1.0 and 300.0, got {self.timeout}"
            )
        if not (0.0 <= self.polite_delay <= 60.0):
            raise ValueError(
                f"polite_delay must be between 0.0 and 60.0, got {self.polite_delay}"
            )
        if not (0.0 <= self.delay_jitter <= 30.0):
            raise ValueError(
                f"delay_jitter must be between 0.0 and 30.0, got {self.delay_jitter}"
            )


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff.

    Parameters
    ----------
    max_attempts : int
        Maximum number of retry attempts (default: 3).
    exponential_base : float
        Base for exponential backoff calculation (default: 2.0).
    max_delay : float
        Maximum delay between retries in seconds (default: 30.0).
    initial_delay : float
        Initial delay between retries in seconds (default: 1.0).
    jitter : bool
        Whether to add random jitter to delays (default: True).

    Raises
    ------
    ValueError
        If max_attempts is outside its valid range.

    Examples
    --------
    >>> config = RetryConfig(max_attempts=5, exponential_base=3.0)
    >>> config.max_attempts
    5
    """

    max_attempts: int = 3
    exponential_base: float = 2.0
    max_delay: float = 30.0
    initial_delay: float = 1.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate retry configuration value ranges.

        Raises
        ------
        ValueError
            If max_attempts is outside its valid range.
        """
        if not (1 <= self.max_attempts <= 10):
            raise ValueError(
                f"max_attempts must be between 1 and 10, got {self.max_attempts}"
            )


@dataclass(frozen=True)
class FetchOptions:
    """Options for API data fetch requests.

    Parameters
    ----------
    use_cache : bool
        Whether to use cached data if available (default: True).
    force_refresh : bool
        Whether to force a fresh fetch, ignoring cache (default: False).

    Examples
    --------
    >>> options = FetchOptions(use_cache=False)
    >>> options.use_cache
    False
    """

    use_cache: bool = True
    force_refresh: bool = False


@dataclass
class TokenInfo:
    """Token information for J-Quants API authentication.

    Stores refresh and id tokens with their expiry timestamps.
    Mutable because tokens are refreshed during the session lifecycle.

    Parameters
    ----------
    refresh_token : str
        The refresh token for obtaining new id tokens.
    id_token : str
        The id token used for API authorization.
    refresh_token_expires_at : datetime
        Expiry timestamp for the refresh token.
    id_token_expires_at : datetime
        Expiry timestamp for the id token.

    Examples
    --------
    >>> from datetime import datetime, timedelta, UTC
    >>> token = TokenInfo(
    ...     refresh_token="rt_xxx",
    ...     id_token="id_xxx",
    ...     refresh_token_expires_at=datetime.now(UTC) + timedelta(days=7),
    ...     id_token_expires_at=datetime.now(UTC) + timedelta(hours=24),
    ... )
    >>> token.is_id_token_expired()
    False
    """

    refresh_token: str = field(default="", repr=False)
    id_token: str = field(default="", repr=False)
    refresh_token_expires_at: datetime = field(
        default_factory=lambda: datetime.min.replace(tzinfo=UTC)
    )
    id_token_expires_at: datetime = field(
        default_factory=lambda: datetime.min.replace(tzinfo=UTC)
    )

    def is_id_token_expired(self) -> bool:
        """Check if the id token has expired.

        Returns
        -------
        bool
            True if the id token is expired or not set.
        """
        return datetime.now(UTC) >= self.id_token_expires_at

    def is_refresh_token_expired(self) -> bool:
        """Check if the refresh token has expired.

        Returns
        -------
        bool
            True if the refresh token is expired or not set.
        """
        return datetime.now(UTC) >= self.refresh_token_expires_at


__all__ = [
    "FetchOptions",
    "JQuantsConfig",
    "RetryConfig",
    "TokenInfo",
]
