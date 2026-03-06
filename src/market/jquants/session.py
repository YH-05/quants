"""HTTP session abstraction for J-Quants API access.

This module provides the ``JQuantsSession`` class, an httpx-based HTTP session
with authentication token management, polite delays (monotonic-clock-based),
SSRF prevention via host whitelist, and exponential backoff retry logic.

The authentication flow follows a 3-stage process:

1. email/password -> ``/token/auth_user`` -> refresh_token
2. refresh_token -> ``/token/auth_refresh`` -> id_token
3. id_token -> Authorization: Bearer header

Tokens are persisted to ``~/.jquants/token.json`` for reuse across sessions.

See Also
--------
market.bse.session : httpx-based session pattern reference.
market.edinet.client : _request + _handle_response pattern reference.
market.jquants.constants : Default values, allowed hosts.
market.jquants.types : JQuantsConfig, RetryConfig, TokenInfo dataclasses.
market.jquants.errors : JQuantsAuthError, JQuantsAPIError exceptions.
"""

import json
import os
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from market.jquants.constants import (
    ALLOWED_HOSTS,
    BASE_URL,
    JQUANTS_MAIL_ADDRESS_ENV,
    JQUANTS_PASSWORD_ENV,
)
from market.jquants.errors import (
    JQuantsAPIError,
    JQuantsAuthError,
    JQuantsRateLimitError,
)
from market.jquants.types import JQuantsConfig, RetryConfig, TokenInfo
from utils_core.logging import get_logger

logger = get_logger(__name__)

# HTTP status code indicating rate limiting
_RATE_LIMIT_STATUS_CODE = 429

# Maximum length of response body stored in JQuantsAPIError (CWE-209 mitigation)
_MAX_RESPONSE_BODY_LOG = 200

# Token validity durations (J-Quants documentation)
_REFRESH_TOKEN_VALIDITY_DAYS = 7
_ID_TOKEN_VALIDITY_HOURS = 24


class JQuantsSession:
    """httpx-based HTTP session for J-Quants API with token authentication.

    Provides automatic authentication token management (login, refresh,
    persistence), polite delays between requests (using ``time.monotonic()``),
    SSRF prevention via host whitelist, response status handling, and
    exponential backoff retry logic.

    Parameters
    ----------
    config : JQuantsConfig | None
        J-Quants configuration. If ``None``, defaults are used.
    retry_config : RetryConfig | None
        Retry configuration. If ``None``, defaults are used.

    Examples
    --------
    >>> with JQuantsSession() as session:
    ...     response = session.get(
    ...         "https://api.jquants.com/v1/listed/info",
    ...     )
    ...     print(response.status_code)
    200
    """

    def __init__(
        self,
        config: JQuantsConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Initialize JQuantsSession with configuration.

        Parameters
        ----------
        config : JQuantsConfig | None
            J-Quants configuration. Defaults to ``JQuantsConfig()``.
        retry_config : RetryConfig | None
            Retry configuration. Defaults to ``RetryConfig()``.
        """
        self._config: JQuantsConfig = config or JQuantsConfig()
        self._retry_config: RetryConfig = retry_config or RetryConfig()
        self._last_request_time: float = 0.0
        self._token_info: TokenInfo = TokenInfo()

        # Create httpx client with timeout and explicit SSL verification
        self._client: httpx.Client = httpx.Client(
            timeout=httpx.Timeout(self._config.timeout),
            verify=True,
        )

        # Try to load tokens from file
        self._load_tokens()

        logger.info(
            "JQuantsSession initialized",
            polite_delay=self._config.polite_delay,
            delay_jitter=self._config.delay_jitter,
            timeout=self._config.timeout,
            max_retry_attempts=self._retry_config.max_attempts,
            has_token=bool(self._token_info.id_token),
        )

    # =========================================================================
    # Public API
    # =========================================================================

    def get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send an authenticated GET request with polite delay and status handling.

        Applies the following before each request:

        1. URL whitelist validation (SSRF prevention)
        2. Token authentication (auto-refresh if expired)
        3. Polite delay (monotonic-clock-based interval control)

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        httpx.Response
            The HTTP response object.

        Raises
        ------
        ValueError
            If the URL host is not in the allowed hosts whitelist.
        JQuantsAuthError
            If authentication fails.
        JQuantsRateLimitError
            If the response status code is 429.
        JQuantsAPIError
            If the response status code indicates an error.
        """
        # 0. URL whitelist validation (SSRF prevention, CWE-918)
        self._validate_url(url)

        # 1. Ensure we have a valid token
        self._ensure_authenticated()

        # 2. Apply polite delay (monotonic-clock-based)
        self._polite_delay()

        # 3. Build headers with auth token
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._token_info.id_token}",
            "Accept": "application/json",
        }

        logger.debug("Sending GET request", url=url)

        # 4. Execute request
        response: httpx.Response = self._client.get(
            url,
            headers=headers,
            params=params,
        )

        # 5. Handle response status
        self._handle_response(response, url)

        logger.debug(
            "GET request completed",
            url=url,
            status_code=response.status_code,
        )
        return response

    def get_with_retry(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request with exponential backoff retry.

        On each failed attempt (rate limit or server error), the request
        is retried after an exponentially increasing delay.

        Parameters
        ----------
        url : str
            The URL to send the GET request to.
        params : dict[str, str] | None
            Optional query parameters for the request.

        Returns
        -------
        httpx.Response
            The HTTP response object.

        Raises
        ------
        JQuantsRateLimitError
            If all retry attempts fail due to rate limiting.
        JQuantsAPIError
            If all retry attempts fail due to server errors.
        """
        last_error: JQuantsRateLimitError | JQuantsAPIError | None = None

        for attempt in range(self._retry_config.max_attempts):
            try:
                response = self.get(url, params=params)

                if attempt > 0:
                    logger.info(
                        "Request succeeded after retry",
                        url=url,
                        attempt=attempt + 1,
                    )
                return response

            except (JQuantsRateLimitError, JQuantsAPIError) as e:
                # Only retry on rate limit and 5xx errors
                if isinstance(e, JQuantsAPIError) and e.status_code < 500:
                    raise
                last_error = e
                logger.warning(
                    "Request failed, will retry",
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self._retry_config.max_attempts,
                    error=str(e),
                )

                # If this is not the last attempt, apply backoff
                if attempt < self._retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.debug(
                        "Backoff before retry",
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    time.sleep(delay)

        # All attempts exhausted
        logger.error(
            "All retry attempts failed",
            url=url,
            max_attempts=self._retry_config.max_attempts,
        )
        assert last_error is not None
        raise last_error

    # =========================================================================
    # Context Manager
    # =========================================================================

    def close(self) -> None:
        """Close the session and release resources."""
        self._client.close()
        logger.debug("JQuantsSession closed")

    def __enter__(self) -> "JQuantsSession":
        """Support context manager protocol.

        Returns
        -------
        JQuantsSession
            Self for use in with statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Close session on context exit."""
        self.close()

    # =========================================================================
    # Authentication
    # =========================================================================

    def _ensure_authenticated(self) -> None:
        """Ensure we have a valid id_token, refreshing or logging in as needed.

        Raises
        ------
        JQuantsAuthError
            If authentication fails after all attempts.
        """
        # If id_token is valid, nothing to do
        if self._token_info.id_token and not self._token_info.is_id_token_expired():
            return

        # Try refreshing id_token using refresh_token
        if (
            self._token_info.refresh_token
            and not self._token_info.is_refresh_token_expired()
        ):
            try:
                self._refresh_id_token()
                return
            except (JQuantsAuthError, JQuantsAPIError):
                logger.warning(
                    "id_token refresh failed, attempting full login",
                )

        # Fall back to full login
        self._login()

    def _login(self) -> None:
        """Authenticate with email/password to obtain refresh_token, then id_token.

        Raises
        ------
        JQuantsAuthError
            If login fails.
        """
        mail_address = self._config.mail_address or os.environ.get(
            JQUANTS_MAIL_ADDRESS_ENV, ""
        )
        password = self._config.password or os.environ.get(JQUANTS_PASSWORD_ENV, "")

        if not mail_address or not password:
            raise JQuantsAuthError(
                "J-Quants credentials not provided. "
                f"Set {JQUANTS_MAIL_ADDRESS_ENV} and {JQUANTS_PASSWORD_ENV} "
                "environment variables or pass them via JQuantsConfig."
            )

        logger.info("Authenticating with J-Quants API (email/password)")

        # Step 1: Get refresh_token
        try:
            response = self._client.post(
                f"{BASE_URL}/token/auth_user",
                json={
                    "mailaddress": mail_address,
                    "password": password,
                },
                timeout=self._config.timeout,
            )
        except httpx.HTTPError as e:
            raise JQuantsAuthError(
                f"Failed to connect to J-Quants auth endpoint: {e}"
            ) from e

        if response.status_code != 200:
            raise JQuantsAuthError(
                f"Login failed: HTTP {response.status_code} - "
                f"{response.text[:_MAX_RESPONSE_BODY_LOG]}"
            )

        data = response.json()
        refresh_token = data.get("refreshToken", "")
        if not refresh_token:
            raise JQuantsAuthError("Login response did not contain refreshToken")

        self._token_info.refresh_token = refresh_token
        self._token_info.refresh_token_expires_at = datetime.now(UTC) + timedelta(
            days=_REFRESH_TOKEN_VALIDITY_DAYS
        )

        logger.info("refresh_token obtained successfully")

        # Step 2: Get id_token using refresh_token
        self._refresh_id_token()

        # Step 3: Persist tokens
        self._save_tokens()

    def _refresh_id_token(self) -> None:
        """Use refresh_token to obtain a new id_token.

        Raises
        ------
        JQuantsAuthError
            If the refresh fails.
        """
        logger.debug("Refreshing id_token")

        try:
            response = self._client.post(
                f"{BASE_URL}/token/auth_refresh",
                params={"refreshtoken": self._token_info.refresh_token},
                timeout=self._config.timeout,
            )
        except httpx.HTTPError as e:
            raise JQuantsAuthError(f"Failed to refresh id_token: {e}") from e

        if response.status_code != 200:
            raise JQuantsAuthError(
                f"id_token refresh failed: HTTP {response.status_code} - "
                f"{response.text[:_MAX_RESPONSE_BODY_LOG]}"
            )

        data = response.json()
        id_token = data.get("idToken", "")
        if not id_token:
            raise JQuantsAuthError("Refresh response did not contain idToken")

        self._token_info.id_token = id_token
        self._token_info.id_token_expires_at = datetime.now(UTC) + timedelta(
            hours=_ID_TOKEN_VALIDITY_HOURS
        )

        # Persist updated tokens
        self._save_tokens()

        logger.info("id_token refreshed successfully")

    # =========================================================================
    # Token Persistence
    # =========================================================================

    def _get_token_file_path(self) -> Path:
        """Resolve the token file path.

        Returns
        -------
        Path
            The absolute path to the token file.
        """
        return Path(self._config.token_file_path).expanduser()

    def _load_tokens(self) -> None:
        """Load tokens from the persistence file if available."""
        token_path = self._get_token_file_path()

        if not token_path.exists():
            logger.debug("Token file not found", path=str(token_path))
            return

        try:
            raw = token_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._token_info = TokenInfo(
                refresh_token=data.get("refresh_token", ""),
                id_token=data.get("id_token", ""),
                refresh_token_expires_at=datetime.fromisoformat(
                    data["refresh_token_expires_at"]
                )
                if data.get("refresh_token_expires_at")
                else datetime.min.replace(tzinfo=UTC),
                id_token_expires_at=datetime.fromisoformat(data["id_token_expires_at"])
                if data.get("id_token_expires_at")
                else datetime.min.replace(tzinfo=UTC),
            )
            logger.info(
                "Tokens loaded from file",
                path=str(token_path),
                has_refresh=bool(self._token_info.refresh_token),
                has_id=bool(self._token_info.id_token),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                "Failed to load tokens from file, will re-authenticate",
                path=str(token_path),
                error=str(e),
            )
            self._token_info = TokenInfo()

    def _save_tokens(self) -> None:
        """Save tokens to the persistence file."""
        token_path = self._get_token_file_path()

        try:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "refresh_token": self._token_info.refresh_token,
                "id_token": self._token_info.id_token,
                "refresh_token_expires_at": self._token_info.refresh_token_expires_at.isoformat(),
                "id_token_expires_at": self._token_info.id_token_expires_at.isoformat(),
            }
            token_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            # Set restrictive permissions (owner-only read/write)
            token_path.chmod(0o600)
            logger.debug("Tokens saved to file", path=str(token_path))
        except OSError as e:
            logger.warning(
                "Failed to save tokens to file",
                path=str(token_path),
                error=str(e),
            )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _validate_url(self, url: str) -> None:
        """Validate URL against the allowed hosts whitelist (SSRF prevention).

        Parameters
        ----------
        url : str
            The URL to validate.

        Raises
        ------
        ValueError
            If the URL host is not in ``ALLOWED_HOSTS``.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"URL scheme must be 'http' or 'https', got '{parsed.scheme}'"
            )
        parsed_host = parsed.netloc
        if parsed_host not in ALLOWED_HOSTS:
            logger.warning(
                "Request blocked: host not in allowed hosts",
                url=url,
                host=parsed_host,
                allowed_hosts=list(ALLOWED_HOSTS),
            )
            raise ValueError(
                f"Host '{parsed_host}' is not in allowed hosts: {sorted(ALLOWED_HOSTS)}"
            )

    def _polite_delay(self) -> None:
        """Apply polite delay between consecutive requests.

        Uses ``time.monotonic()`` to measure elapsed time since the
        last request. Sleeps for the remaining delay if not enough
        time has passed. Adds random jitter to avoid thundering herd.
        """
        now = time.monotonic()

        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            required_delay = self._config.polite_delay + random.uniform(  # nosec B311
                0, self._config.delay_jitter
            )
            remaining = required_delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
                logger.debug("Polite delay applied", delay_seconds=remaining)

        self._last_request_time = time.monotonic()

    def _handle_response(self, response: httpx.Response, url: str) -> None:
        """Check response status and raise appropriate exceptions.

        Parameters
        ----------
        response : httpx.Response
            The HTTP response to check.
        url : str
            The request URL for error context.

        Raises
        ------
        JQuantsRateLimitError
            If HTTP 429 is returned.
        JQuantsAPIError
            If HTTP 4xx or 5xx is returned.
        """
        status = response.status_code

        # 429: rate limit
        if status == _RATE_LIMIT_STATUS_CODE:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = int(retry_after_header) if retry_after_header else None
            logger.warning(
                "Rate limit detected",
                url=url,
                status_code=status,
                retry_after=retry_after,
            )
            raise JQuantsRateLimitError(
                message=f"Rate limit detected: HTTP {status}",
                url=url,
                retry_after=retry_after,
            )

        # 4xx: client error (except 429)
        if 400 <= status < 500:
            logger.warning(
                "Client error",
                url=url,
                status_code=status,
            )
            raise JQuantsAPIError(
                message=f"Client error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
            )

        # 5xx: server error
        if status >= 500:
            logger.warning(
                "Server error",
                url=url,
                status_code=status,
            )
            raise JQuantsAPIError(
                message=f"Server error: HTTP {status}",
                url=url,
                status_code=status,
                response_body=response.text[:_MAX_RESPONSE_BODY_LOG],
            )

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Parameters
        ----------
        attempt : int
            Current attempt number (0-indexed).

        Returns
        -------
        float
            Delay in seconds.
        """
        delay = min(
            self._retry_config.initial_delay
            * (self._retry_config.exponential_base**attempt),
            self._retry_config.max_delay,
        )
        if self._retry_config.jitter:
            delay *= 0.5 + random.random()  # nosec B311
        return delay


__all__ = ["JQuantsSession"]
