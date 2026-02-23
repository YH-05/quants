"""HTTP セッション管理モジュール."""

from typing import Literal

from curl_cffi import requests
from curl_cffi.requests import AsyncSession


def create_session(
    impersonate: Literal["chrome", "chrome131", "safari", "firefox"] = "chrome131",
    proxy: str | None = None,
) -> requests.Session:
    """ブラウザを偽装した HTTP セッションを作成する.

    Parameters
    ----------
    impersonate : str
        偽装するブラウザ（chrome131, chrome, safari, firefox）
    proxy : str | None
        プロキシ URL（例: "http://user:pass@host:port"）

    Returns
    -------
    requests.Session
        設定済みセッション

    Examples
    --------
    >>> session = create_session()
    >>> session = create_session(impersonate="safari", proxy="http://localhost:8080")
    """
    session = requests.Session(impersonate=impersonate)

    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    return session


def create_async_session(
    impersonate: Literal["chrome", "chrome131", "safari", "firefox"] = "chrome131",
    proxy: str | None = None,
) -> AsyncSession:
    """ブラウザを偽装した非同期 HTTP セッションを作成する.

    Parameters
    ----------
    impersonate : str
        偽装するブラウザ（chrome131, chrome, safari, firefox）
    proxy : str | None
        プロキシ URL（例: "http://user:pass@host:port"）

    Returns
    -------
    AsyncSession
        設定済み非同期セッション

    Examples
    --------
    >>> session = create_async_session()
    >>> session = create_async_session(impersonate="safari", proxy="http://localhost:8080")
    """
    return AsyncSession(
        impersonate=impersonate,
        proxy=proxy,
    )
