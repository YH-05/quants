"""Tests for market.edinet_api.types module.

Tests verify all type definitions for the EDINET disclosure API module,
including Enum (DocumentType), frozen dataclasses (EdinetApiConfig,
RetryConfig, DisclosureDocument), and module exports.

Test TODO List:
- [x] Module exports: __all__ completeness and importability
- [x] DocumentType Enum: values, str inheritance, member count
- [x] EdinetApiConfig: frozen, defaults from constants, field types
- [x] EdinetApiConfig: timeout/polite_delay/delay_jitter range validation
- [x] RetryConfig: frozen, defaults, field types
- [x] RetryConfig: max_attempts range validation
- [x] DisclosureDocument: frozen, all fields, field types
"""

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest

from market.edinet_api.constants import (
    DEFAULT_DELAY_JITTER,
    DEFAULT_POLITE_DELAY,
    DEFAULT_TIMEOUT,
)
from market.edinet_api.types import (
    DisclosureDocument,
    DocumentType,
    EdinetApiConfig,
    RetryConfig,
    __all__,
)

# =============================================================================
# Module exports
# =============================================================================


class TestModuleExports:
    """Test module __all__ exports and structure."""

    def test_正常系_モジュールがインポートできる(self) -> None:
        """types モジュールが正常にインポートできること。"""
        from market.edinet_api import types

        assert types is not None

    def test_正常系_allが定義されている(self) -> None:
        """__all__ がリストとして定義されていること。"""
        assert isinstance(__all__, list)
        assert len(__all__) > 0

    def test_正常系_allの全項目がモジュールに存在する(self) -> None:
        """__all__ の全項目がモジュールの属性として存在すること。"""
        from market.edinet_api import types

        for name in __all__:
            assert hasattr(types, name), f"{name} is not defined in types module"

    def test_正常系_allが4項目を含む(self) -> None:
        """__all__ が全4型定義をエクスポートしていること。"""
        expected = {
            "DisclosureDocument",
            "DocumentType",
            "EdinetApiConfig",
            "RetryConfig",
        }
        assert set(__all__) == expected


# =============================================================================
# DocumentType Enum
# =============================================================================


class TestDocumentType:
    """DocumentType Enum のテスト。"""

    def test_正常系_strとEnumを継承している(self) -> None:
        """DocumentType が str と Enum を継承していること。"""
        assert issubclass(DocumentType, str)
        assert issubclass(DocumentType, Enum)

    def test_正常系_有報メンバーが存在する(self) -> None:
        """ANNUAL_REPORT メンバーが存在すること。"""
        assert DocumentType.ANNUAL_REPORT.value == "有価証券報告書"

    def test_正常系_四半期報告書メンバーが存在する(self) -> None:
        """QUARTERLY_REPORT メンバーが存在すること。"""
        assert DocumentType.QUARTERLY_REPORT.value == "四半期報告書"

    def test_正常系_臨時報告書メンバーが存在する(self) -> None:
        """EXTRAORDINARY_REPORT メンバーが存在すること。"""
        assert DocumentType.EXTRAORDINARY_REPORT.value == "臨時報告書"

    def test_正常系_8種類のメンバーが存在する(self) -> None:
        """DocumentType が8種類のメンバーを含むこと。"""
        assert len(DocumentType) == 8

    def test_正常系_value属性が日本語文字列を返す(self) -> None:
        """value 属性が日本語文字列を返すこと。"""
        assert DocumentType.ANNUAL_REPORT.value == "有価証券報告書"

    def test_正常系_全メンバーが空でない文字列(self) -> None:
        """全メンバーの値が空でない文字列であること。"""
        for member in DocumentType:
            assert isinstance(member.value, str)
            assert len(member.value) > 0


# =============================================================================
# EdinetApiConfig dataclass
# =============================================================================


class TestEdinetApiConfig:
    """EdinetApiConfig dataclass のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルト値で初期化されること。"""
        config = EdinetApiConfig()

        assert config.api_key == ""
        assert config.timeout == DEFAULT_TIMEOUT
        assert config.polite_delay == DEFAULT_POLITE_DELAY
        assert config.delay_jitter == DEFAULT_DELAY_JITTER

    def test_正常系_カスタム値で初期化できる(self) -> None:
        """カスタム値で初期化されること。"""
        config = EdinetApiConfig(
            api_key="test-key",
            timeout=60.0,
            polite_delay=1.0,
            delay_jitter=0.2,
        )

        assert config.api_key == "test-key"
        assert config.timeout == 60.0
        assert config.polite_delay == 1.0
        assert config.delay_jitter == 0.2

    def test_正常系_frozenで変更不可(self) -> None:
        """frozen=True で属性変更ができないこと。"""
        config = EdinetApiConfig()

        with pytest.raises(FrozenInstanceError):
            config.api_key = "new-key"  # type: ignore[misc]

    def test_異常系_timeoutが範囲外でValueError(self) -> None:
        """timeout が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="timeout must be between"):
            EdinetApiConfig(timeout=0.5)

        with pytest.raises(ValueError, match="timeout must be between"):
            EdinetApiConfig(timeout=301.0)

    def test_異常系_polite_delayが範囲外でValueError(self) -> None:
        """polite_delay が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="polite_delay must be between"):
            EdinetApiConfig(polite_delay=-0.1)

        with pytest.raises(ValueError, match="polite_delay must be between"):
            EdinetApiConfig(polite_delay=61.0)

    def test_異常系_delay_jitterが範囲外でValueError(self) -> None:
        """delay_jitter が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="delay_jitter must be between"):
            EdinetApiConfig(delay_jitter=-0.1)

        with pytest.raises(ValueError, match="delay_jitter must be between"):
            EdinetApiConfig(delay_jitter=31.0)

    def test_エッジケース_境界値で初期化可能(self) -> None:
        """各フィールドの境界値で初期化できること。"""
        config = EdinetApiConfig(
            timeout=1.0,
            polite_delay=0.0,
            delay_jitter=0.0,
        )
        assert config.timeout == 1.0
        assert config.polite_delay == 0.0
        assert config.delay_jitter == 0.0

        config_max = EdinetApiConfig(
            timeout=300.0,
            polite_delay=60.0,
            delay_jitter=30.0,
        )
        assert config_max.timeout == 300.0
        assert config_max.polite_delay == 60.0
        assert config_max.delay_jitter == 30.0


# =============================================================================
# RetryConfig dataclass
# =============================================================================


class TestRetryConfig:
    """RetryConfig dataclass のテスト。"""

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """デフォルト値で初期化されること。"""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_正常系_カスタム値で初期化できる(self) -> None:
        """カスタム値で初期化されること。"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_正常系_frozenで変更不可(self) -> None:
        """frozen=True で属性変更ができないこと。"""
        config = RetryConfig()

        with pytest.raises(FrozenInstanceError):
            config.max_attempts = 5  # type: ignore[misc]

    def test_異常系_max_attemptsが範囲外でValueError(self) -> None:
        """max_attempts が範囲外の場合 ValueError が発生すること。"""
        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=0)

        with pytest.raises(ValueError, match="max_attempts must be between"):
            RetryConfig(max_attempts=11)

    def test_エッジケース_境界値で初期化可能(self) -> None:
        """max_attempts の境界値で初期化できること。"""
        config_min = RetryConfig(max_attempts=1)
        assert config_min.max_attempts == 1

        config_max = RetryConfig(max_attempts=10)
        assert config_max.max_attempts == 10


# =============================================================================
# DisclosureDocument dataclass
# =============================================================================


class TestDisclosureDocument:
    """DisclosureDocument dataclass のテスト。"""

    def test_正常系_全フィールドで初期化できる(self) -> None:
        """全フィールドで初期化されること。"""
        doc = DisclosureDocument(
            doc_id="S100ABCD",
            edinet_code="E00001",
            filer_name="テスト株式会社",
            doc_description="有価証券報告書",
            submit_date_time="2025-01-15 09:30",
            doc_type_code="120",
            sec_code="72010",
            jcn="1234567890123",
        )

        assert doc.doc_id == "S100ABCD"
        assert doc.edinet_code == "E00001"
        assert doc.filer_name == "テスト株式会社"
        assert doc.doc_description == "有価証券報告書"
        assert doc.submit_date_time == "2025-01-15 09:30"
        assert doc.doc_type_code == "120"
        assert doc.sec_code == "72010"
        assert doc.jcn == "1234567890123"

    def test_正常系_オプショナルフィールドのデフォルト値(self) -> None:
        """オプショナルフィールドのデフォルト値が None であること。"""
        doc = DisclosureDocument(
            doc_id="S100ABCD",
            edinet_code="E00001",
            filer_name="テスト株式会社",
            doc_description="有価証券報告書",
            submit_date_time="2025-01-15 09:30",
        )

        assert doc.doc_type_code is None
        assert doc.sec_code is None
        assert doc.jcn is None

    def test_正常系_frozenで変更不可(self) -> None:
        """frozen=True で属性変更ができないこと。"""
        doc = DisclosureDocument(
            doc_id="S100ABCD",
            edinet_code="E00001",
            filer_name="テスト株式会社",
            doc_description="有価証券報告書",
            submit_date_time="2025-01-15 09:30",
        )

        with pytest.raises(FrozenInstanceError):
            doc.doc_id = "S100EFGH"  # type: ignore[misc]

    def test_正常系_edinet_codeがNoneでも初期化可能(self) -> None:
        """edinet_code が None でも初期化できること。"""
        doc = DisclosureDocument(
            doc_id="S100ABCD",
            edinet_code=None,
            filer_name="テスト株式会社",
            doc_description="有価証券報告書",
            submit_date_time="2025-01-15 09:30",
        )

        assert doc.edinet_code is None
