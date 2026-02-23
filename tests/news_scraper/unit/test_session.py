"""session.py の単体テスト.

create_session() と create_async_session() の動作を検証する。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from news_scraper.session import create_async_session, create_session


class TestCreateSession:
    """create_session() のテスト."""

    def test_正常系_デフォルト引数でセッション生成できる(self) -> None:
        """デフォルト引数で同期セッションを生成できることを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            session = create_session()

        mock_session_cls.assert_called_once_with(impersonate="chrome131")
        assert session is mock_instance

    def test_正常系_chrome131で生成できる(self) -> None:
        """impersonate='chrome131' でセッションを生成できることを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            session = create_session(impersonate="chrome131")

        mock_session_cls.assert_called_once_with(impersonate="chrome131")
        assert session is mock_instance

    def test_正常系_safariで生成できる(self) -> None:
        """impersonate='safari' でセッションを生成できることを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            session = create_session(impersonate="safari")

        mock_session_cls.assert_called_once_with(impersonate="safari")
        assert session is mock_instance

    def test_正常系_firefoxで生成できる(self) -> None:
        """impersonate='firefox' でセッションを生成できることを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            session = create_session(impersonate="firefox")

        mock_session_cls.assert_called_once_with(impersonate="firefox")
        assert session is mock_instance

    def test_正常系_chromeで生成できる(self) -> None:
        """impersonate='chrome' でセッションを生成できることを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            session = create_session(impersonate="chrome")

        mock_session_cls.assert_called_once_with(impersonate="chrome")
        assert session is mock_instance

    def test_正常系_proxyなしでセッション生成できる(self) -> None:
        """proxy=None でセッションを生成するとき proxies が設定されないことを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            create_session(proxy=None)

        # proxies 属性は設定されない
        assert not hasattr(mock_instance, "proxies") or mock_instance.proxies != {
            "http": None,
            "https": None,
        }

    def test_正常系_proxy付きでセッション生成できる(self) -> None:
        """proxy 付きでセッションを生成するとき proxies が設定されることを確認。"""
        proxy_url = "http://proxy.example.com:8080"

        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            create_session(proxy=proxy_url)

        assert mock_instance.proxies == {"http": proxy_url, "https": proxy_url}

    def test_正常系_proxyなしではproxiesが変更されない(self) -> None:
        """proxy=None のとき proxies 属性が変更されないことを確認。"""
        with patch("news_scraper.session.requests.Session") as mock_session_cls:
            mock_instance = MagicMock()
            mock_session_cls.return_value = mock_instance

            create_session(proxy=None)

        # proxies 属性への代入が呼ばれていない
        assert "proxies" not in mock_instance.__dict__


class TestCreateAsyncSession:
    """create_async_session() のテスト."""

    def test_正常系_デフォルト引数で非同期セッション生成できる(self) -> None:
        """デフォルト引数で非同期セッションを生成できることを確認。"""
        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session()

        mock_async_cls.assert_called_once_with(
            impersonate="chrome131",
            proxy=None,
        )
        assert session is mock_instance

    def test_正常系_safariで非同期セッション生成できる(self) -> None:
        """impersonate='safari' で非同期セッションを生成できることを確認。"""
        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session(impersonate="safari")

        mock_async_cls.assert_called_once_with(
            impersonate="safari",
            proxy=None,
        )
        assert session is mock_instance

    def test_正常系_proxy付きで非同期セッション生成できる(self) -> None:
        """proxy 付きで非同期セッションを生成できることを確認。"""
        proxy_url = "http://proxy.example.com:8080"

        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session(proxy=proxy_url)

        mock_async_cls.assert_called_once_with(
            impersonate="chrome131",
            proxy=proxy_url,
        )
        assert session is mock_instance

    def test_正常系_chrome131で非同期セッション生成できる(self) -> None:
        """impersonate='chrome131' で非同期セッションを生成できることを確認。"""
        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session(impersonate="chrome131")

        mock_async_cls.assert_called_once_with(
            impersonate="chrome131",
            proxy=None,
        )
        assert session is mock_instance

    def test_正常系_firefoxで非同期セッション生成できる(self) -> None:
        """impersonate='firefox' で非同期セッションを生成できることを確認。"""
        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session(impersonate="firefox")

        mock_async_cls.assert_called_once_with(
            impersonate="firefox",
            proxy=None,
        )
        assert session is mock_instance

    def test_正常系_全引数指定で非同期セッション生成できる(self) -> None:
        """全引数を指定して非同期セッションを生成できることを確認。"""
        proxy_url = "http://user:pass@proxy.example.com:3128"

        with patch("news_scraper.session.AsyncSession") as mock_async_cls:
            mock_instance = MagicMock()
            mock_async_cls.return_value = mock_instance

            session = create_async_session(
                impersonate="chrome",
                proxy=proxy_url,
            )

        mock_async_cls.assert_called_once_with(
            impersonate="chrome",
            proxy=proxy_url,
        )
        assert session is mock_instance
