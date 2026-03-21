"""Custom exception classes for the Polymarket API module.

This module provides a hierarchy of exception classes for handling
various error conditions specific to Polymarket API operations,
including API response errors, rate limiting, data validation errors,
and resource-not-found errors.

Exception Hierarchy
-------------------
PolymarketError (base, inherits Exception)
    PolymarketAPIError (API response error - 4xx, 5xx)
        PolymarketRateLimitError (rate limit exceeded - 429)
    PolymarketValidationError (data validation failure)
    PolymarketNotFoundError (resource not found)

Notes
-----
This follows the same ``Exception``-direct-inheritance pattern used by
``market.jquants.errors.JQuantsError`` and ``market.eodhd.errors.EodhdError``
to avoid circular imports with ``market.errors.MarketError``.

Polymarket APIs are public and do not require authentication, so there is
no ``AuthError`` class. Instead, ``PolymarketNotFoundError`` is provided for
resource-not-found scenarios (markets, events, conditions).

See Also
--------
market.jquants.errors : J-Quants error hierarchy (reference implementation).
market.eodhd.errors : EODHD error hierarchy (reference implementation).
"""


class PolymarketError(Exception):
    """Base exception for all Polymarket API operations.

    All Polymarket-specific exceptions inherit from this class,
    providing a single catch point for callers that need to handle
    any Polymarket-related failure generically.

    Parameters
    ----------
    message : str
        Human-readable error message describing the failure.

    Attributes
    ----------
    message : str
        The error message.

    Examples
    --------
    >>> try:
    ...     raise PolymarketError("Polymarket API operation failed")
    ... except PolymarketError as e:
    ...     print(e.message)
    Polymarket API operation failed
    """

    def __init__(self, message: str) -> None:
        """Initialize PolymarketError."""
        super().__init__(message)
        self.message = message


class PolymarketAPIError(PolymarketError):
    """Exception raised when the Polymarket API returns an error response.

    This exception is raised when a request to the Polymarket API
    returns a non-success HTTP status code (4xx or 5xx).

    Parameters
    ----------
    message : str
        Human-readable error message describing the API failure.
    url : str
        The API endpoint URL that returned the error.
    status_code : int
        The HTTP status code returned by the API.
    response_body : str
        The raw response body returned by the API.

    Attributes
    ----------
    url : str
        The API endpoint URL.
    status_code : int
        The HTTP status code.
    response_body : str
        The raw response body.

    Examples
    --------
    >>> raise PolymarketAPIError(
    ...     "API returned HTTP 500",
    ...     url="https://gamma-api.polymarket.com/markets",
    ...     status_code=500,
    ...     response_body='{"error": "Internal Server Error"}',
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str,
        status_code: int,
        response_body: str,
    ) -> None:
        """Initialize PolymarketAPIError."""
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.response_body = response_body


class PolymarketRateLimitError(PolymarketAPIError):
    """Exception raised when the Polymarket API rate limit is exceeded.

    This exception inherits from ``PolymarketAPIError`` because a rate
    limit response is itself an HTTP error (status code 429).

    Parameters
    ----------
    message : str
        Human-readable error message describing the rate limit.
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The number of seconds to wait before retrying.

    Attributes
    ----------
    url : str | None
        The URL that triggered the rate limit.
    retry_after : int | None
        The suggested retry delay in seconds.

    Examples
    --------
    >>> raise PolymarketRateLimitError(
    ...     "Rate limit exceeded",
    ...     url="https://gamma-api.polymarket.com/markets",
    ...     retry_after=60,
    ... )
    """

    def __init__(
        self,
        message: str,
        url: str | None,
        retry_after: int | None,
    ) -> None:
        """Initialize PolymarketRateLimitError."""
        # Pass url to PolymarketAPIError with status_code=429 and empty body
        super().__init__(
            message=message,
            url=url or "",
            status_code=429,
            response_body="",
        )
        # Override url to preserve None if passed
        self.url = url
        self.retry_after = retry_after


class PolymarketValidationError(PolymarketError):
    """Exception raised when Polymarket data validation fails.

    Parameters
    ----------
    message : str
        Human-readable error message describing the validation failure.
    field : str
        The field that failed validation.
    value : object
        The invalid value that caused the validation failure.

    Attributes
    ----------
    field : str
        The field that failed validation.
    value : object
        The invalid value.

    Examples
    --------
    >>> raise PolymarketValidationError(
    ...     "Invalid condition ID format",
    ...     field="condition_id",
    ...     value="",
    ... )
    """

    def __init__(
        self,
        message: str,
        field: str,
        value: object,
    ) -> None:
        """Initialize PolymarketValidationError."""
        super().__init__(message)
        self.field = field
        self.value = value


class PolymarketNotFoundError(PolymarketError):
    """Exception raised when a Polymarket resource is not found.

    This exception is raised when a requested resource (market, event,
    condition, etc.) does not exist or is no longer available.

    Parameters
    ----------
    message : str
        Human-readable error message describing the not-found condition.
    resource_type : str
        The type of resource that was not found (e.g., "market", "event").
    resource_id : str
        The identifier of the resource that was not found.

    Attributes
    ----------
    resource_type : str
        The type of resource that was not found.
    resource_id : str
        The identifier of the resource that was not found.

    Examples
    --------
    >>> raise PolymarketNotFoundError(
    ...     "Market not found",
    ...     resource_type="market",
    ...     resource_id="0x1234567890abcdef",
    ... )
    """

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Initialize PolymarketNotFoundError."""
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


__all__ = [
    "PolymarketAPIError",
    "PolymarketError",
    "PolymarketNotFoundError",
    "PolymarketRateLimitError",
    "PolymarketValidationError",
]
