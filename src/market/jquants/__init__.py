"""J-Quants API client module.

This package provides a client for the JPX J-Quants API
(https://api.jquants.com/v1) to retrieve Japanese stock market data.

Modules
-------
constants : API URL, environment variable names, default configuration.
errors : Exception hierarchy for J-Quants API operations.
types : Configuration dataclasses and token management.
session : httpx-based HTTP session with authentication token management.
client : High-level API client with caching.
cache : Cache helper with TTL constants.

Public API
----------
JQuantsClient
    High-level API client with typed methods and caching.
JQuantsConfig
    Configuration for authentication and HTTP behaviour.
RetryConfig
    Configuration for retry behaviour with exponential backoff.
FetchOptions
    Options for controlling cache behaviour per request.
TokenInfo
    Token storage with expiry tracking.

Error Classes
-------------
JQuantsError
    Base exception for all J-Quants API operations.
JQuantsAPIError
    Exception raised when the API returns an error response.
JQuantsRateLimitError
    Exception raised when the API rate limit is exceeded.
JQuantsValidationError
    Exception raised when data validation fails.
JQuantsAuthError
    Exception raised when authentication fails.
"""

from market.jquants.client import JQuantsClient
from market.jquants.errors import (
    JQuantsAPIError,
    JQuantsAuthError,
    JQuantsError,
    JQuantsRateLimitError,
    JQuantsValidationError,
)
from market.jquants.session import JQuantsSession
from market.jquants.types import (
    FetchOptions,
    JQuantsConfig,
    RetryConfig,
    TokenInfo,
)

__all__ = [
    "FetchOptions",
    "JQuantsAPIError",
    "JQuantsAuthError",
    "JQuantsClient",
    "JQuantsConfig",
    "JQuantsError",
    "JQuantsRateLimitError",
    "JQuantsSession",
    "JQuantsValidationError",
    "RetryConfig",
    "TokenInfo",
]
