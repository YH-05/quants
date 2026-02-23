"""Unit tests for market.bloomberg.types module.

TDD Red Phase: These tests are designed to fail initially.
The implementation (market.bloomberg.types) does not exist yet.

Test TODO List:
- [x] IDType enum: ticker, sedol, cusip, isin, figi values
- [x] Periodicity enum: DAILY, WEEKLY, MONTHLY, QUARTERLY, YEARLY values
- [x] BloombergFetchOptions: initialization with defaults and custom values
- [x] BloombergDataResult: initialization and properties
- [x] OverrideOption: initialization for overrides
- [x] ChunkConfig: initialization with defaults and custom values
- [x] EarningsInfo: initialization with required fields
- [x] IdentifierConversionResult: initialization with required fields
"""

from datetime import datetime

import pandas as pd
import pytest


class TestIDType:
    """Tests for IDType enum.

    IDType represents the type of security identifier used in Bloomberg.
    Supported types: ticker, sedol, cusip, isin, figi
    """

    def test_正常系_全てのIDタイプが定義されている(self) -> None:
        """必要なIDタイプが全て定義されていることを確認。"""
        from market.bloomberg.types import IDType

        assert hasattr(IDType, "TICKER")
        assert hasattr(IDType, "SEDOL")
        assert hasattr(IDType, "CUSIP")
        assert hasattr(IDType, "ISIN")
        assert hasattr(IDType, "FIGI")

    @pytest.mark.parametrize(
        "id_type_name,expected_value",
        [
            ("TICKER", "ticker"),
            ("SEDOL", "sedol"),
            ("CUSIP", "cusip"),
            ("ISIN", "isin"),
            ("FIGI", "figi"),
        ],
    )
    def test_正常系_IDタイプの値が正しい(
        self, id_type_name: str, expected_value: str
    ) -> None:
        """各IDTypeの値がBloomberg形式であることを確認。"""
        from market.bloomberg.types import IDType

        id_type = getattr(IDType, id_type_name)
        assert id_type.value == expected_value

    def test_正常系_str型を継承(self) -> None:
        """IDType が str を継承していることを確認。"""
        from market.bloomberg.types import IDType

        assert isinstance(IDType.TICKER, str)


class TestPeriodicity:
    """Tests for Periodicity enum.

    Periodicity represents the frequency of data in Bloomberg.
    """

    def test_正常系_全ての周期が定義されている(self) -> None:
        """必要な周期が全て定義されていることを確認。"""
        from market.bloomberg.types import Periodicity

        assert hasattr(Periodicity, "DAILY")
        assert hasattr(Periodicity, "WEEKLY")
        assert hasattr(Periodicity, "MONTHLY")
        assert hasattr(Periodicity, "QUARTERLY")
        assert hasattr(Periodicity, "YEARLY")

    @pytest.mark.parametrize(
        "periodicity_name,expected_value",
        [
            ("DAILY", "DAILY"),
            ("WEEKLY", "WEEKLY"),
            ("MONTHLY", "MONTHLY"),
            ("QUARTERLY", "QUARTERLY"),
            ("YEARLY", "YEARLY"),
        ],
    )
    def test_正常系_周期の値が正しい(
        self, periodicity_name: str, expected_value: str
    ) -> None:
        """各Periodicityの値がBloomberg形式であることを確認。"""
        from market.bloomberg.types import Periodicity

        periodicity = getattr(Periodicity, periodicity_name)
        assert periodicity.value == expected_value

    def test_正常系_str型を継承(self) -> None:
        """Periodicity が str を継承していることを確認。"""
        from market.bloomberg.types import Periodicity

        assert isinstance(Periodicity.DAILY, str)


class TestDataSource:
    """Tests for DataSource enum."""

    def test_正常系_BLOOMBERGが定義されている(self) -> None:
        """DataSource.BLOOMBERG が定義されていることを確認。"""
        from market.bloomberg.types import DataSource

        assert hasattr(DataSource, "BLOOMBERG")
        assert DataSource.BLOOMBERG.value == "bloomberg"


class TestOverrideOption:
    """Tests for OverrideOption dataclass.

    OverrideOption represents a Bloomberg override setting.
    """

    def test_正常系_基本的な初期化(self) -> None:
        """OverrideOption が基本パラメータで初期化されることを確認。"""
        from market.bloomberg.types import OverrideOption

        override = OverrideOption(field="CRNCY", value="USD")
        assert override.field == "CRNCY"
        assert override.value == "USD"

    def test_正常系_数値オーバーライド(self) -> None:
        """OverrideOption が数値でも初期化されることを確認。"""
        from market.bloomberg.types import OverrideOption

        override = OverrideOption(field="BEST_FPERIOD_OVERRIDE", value=1)
        assert override.field == "BEST_FPERIOD_OVERRIDE"
        assert override.value == 1


class TestBloombergFetchOptions:
    """Tests for BloombergFetchOptions dataclass.

    BloombergFetchOptions contains all options for Bloomberg data fetching.
    """

    def test_正常系_必須パラメータのみで初期化(self) -> None:
        """BloombergFetchOptions が必須パラメータのみで初期化されることを確認。"""
        from market.bloomberg.types import BloombergFetchOptions, IDType

        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
        )

        assert options.securities == ["AAPL US Equity"]
        assert options.fields == ["PX_LAST"]
        assert options.id_type == IDType.TICKER  # デフォルト値
        assert options.start_date is None
        assert options.end_date is None
        assert options.overrides == []

    def test_正常系_全パラメータで初期化(self) -> None:
        """BloombergFetchOptions が全パラメータで初期化されることを確認。"""
        from market.bloomberg.types import (
            BloombergFetchOptions,
            IDType,
            OverrideOption,
            Periodicity,
        )

        overrides = [OverrideOption(field="CRNCY", value="JPY")]
        options = BloombergFetchOptions(
            securities=["7203 JP Equity", "6758 JP Equity"],
            fields=["PX_LAST", "PX_VOLUME"],
            id_type=IDType.TICKER,
            start_date="2024-01-01",
            end_date="2024-12-31",
            periodicity=Periodicity.DAILY,
            overrides=overrides,
        )

        assert options.securities == ["7203 JP Equity", "6758 JP Equity"]
        assert options.fields == ["PX_LAST", "PX_VOLUME"]
        assert options.id_type == IDType.TICKER
        assert options.start_date == "2024-01-01"
        assert options.end_date == "2024-12-31"
        assert options.periodicity == Periodicity.DAILY
        assert len(options.overrides) == 1

    def test_正常系_datetime型の日付で初期化(self) -> None:
        """BloombergFetchOptions がdatetime型の日付で初期化されることを確認。"""
        from market.bloomberg.types import BloombergFetchOptions

        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        options = BloombergFetchOptions(
            securities=["AAPL US Equity"],
            fields=["PX_LAST"],
            start_date=start,
            end_date=end,
        )

        assert options.start_date == start
        assert options.end_date == end

    @pytest.mark.parametrize(
        "id_type_name",
        ["TICKER", "SEDOL", "CUSIP", "ISIN", "FIGI"],
    )
    def test_パラメトライズ_各IDタイプで初期化できる(self, id_type_name: str) -> None:
        """各IDタイプでBloombergFetchOptionsが初期化できることを確認。"""
        from market.bloomberg.types import BloombergFetchOptions, IDType

        id_type = getattr(IDType, id_type_name)
        options = BloombergFetchOptions(
            securities=["TEST"],
            fields=["PX_LAST"],
            id_type=id_type,
        )

        assert options.id_type == id_type


class TestBloombergDataResult:
    """Tests for BloombergDataResult dataclass.

    BloombergDataResult represents the result of a Bloomberg data fetch operation.
    """

    def test_正常系_基本的な初期化(self) -> None:
        """BloombergDataResult が基本パラメータで初期化されることを確認。"""
        from market.bloomberg.types import BloombergDataResult, DataSource

        df = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02"],
                "PX_LAST": [150.0, 151.0],
            }
        )

        result = BloombergDataResult(
            security="AAPL US Equity",
            data=df,
            source=DataSource.BLOOMBERG,
            fetched_at=datetime.now(),
        )

        assert result.security == "AAPL US Equity"
        assert result.source == DataSource.BLOOMBERG
        assert result.from_cache is False  # デフォルト値
        assert len(result.data) == 2

    def test_正常系_is_emptyプロパティ_空データ(self) -> None:
        """空の DataFrame の場合 is_empty が True を返すことを確認。"""
        from market.bloomberg.types import BloombergDataResult, DataSource

        result = BloombergDataResult(
            security="AAPL US Equity",
            data=pd.DataFrame(),
            source=DataSource.BLOOMBERG,
            fetched_at=datetime.now(),
        )

        assert result.is_empty is True

    def test_正常系_is_emptyプロパティ_データあり(self) -> None:
        """データがある場合 is_empty が False を返すことを確認。"""
        from market.bloomberg.types import BloombergDataResult, DataSource

        df = pd.DataFrame({"PX_LAST": [150.0]})
        result = BloombergDataResult(
            security="AAPL US Equity",
            data=df,
            source=DataSource.BLOOMBERG,
            fetched_at=datetime.now(),
        )

        assert result.is_empty is False

    def test_正常系_row_countプロパティ(self) -> None:
        """row_count プロパティが正しい行数を返すことを確認。"""
        from market.bloomberg.types import BloombergDataResult, DataSource

        df = pd.DataFrame({"PX_LAST": [150.0, 151.0, 152.0]})
        result = BloombergDataResult(
            security="AAPL US Equity",
            data=df,
            source=DataSource.BLOOMBERG,
            fetched_at=datetime.now(),
        )

        assert result.row_count == 3

    def test_正常系_metadataが設定できる(self) -> None:
        """metadata フィールドが設定できることを確認。"""
        from market.bloomberg.types import BloombergDataResult, DataSource

        result = BloombergDataResult(
            security="AAPL US Equity",
            data=pd.DataFrame(),
            source=DataSource.BLOOMBERG,
            fetched_at=datetime.now(),
            metadata={"request_id": "123", "response_time_ms": 150},
        )

        assert result.metadata["request_id"] == "123"
        assert result.metadata["response_time_ms"] == 150


class TestNewsStory:
    """Tests for NewsStory dataclass.

    NewsStory represents a Bloomberg news article.
    """

    def test_正常系_基本的な初期化(self) -> None:
        """NewsStory が基本パラメータで初期化されることを確認。"""
        from market.bloomberg.types import NewsStory

        story = NewsStory(
            story_id="BBG123456789",
            headline="Apple Reports Q4 Earnings",
            datetime=datetime(2024, 1, 15, 9, 30),
        )

        assert story.story_id == "BBG123456789"
        assert story.headline == "Apple Reports Q4 Earnings"
        assert story.datetime == datetime(2024, 1, 15, 9, 30)
        assert story.body is None  # デフォルト値

    def test_正常系_本文付きで初期化(self) -> None:
        """NewsStory が本文付きで初期化されることを確認。"""
        from market.bloomberg.types import NewsStory

        story = NewsStory(
            story_id="BBG123456789",
            headline="Apple Reports Q4 Earnings",
            datetime=datetime(2024, 1, 15, 9, 30),
            body="Apple Inc. reported earnings...",
            source="Bloomberg News",
        )

        assert story.body == "Apple Inc. reported earnings..."
        assert story.source == "Bloomberg News"


class TestFieldInfo:
    """Tests for FieldInfo dataclass.

    FieldInfo represents Bloomberg field metadata.
    """

    def test_正常系_基本的な初期化(self) -> None:
        """FieldInfo が基本パラメータで初期化されることを確認。"""
        from market.bloomberg.types import FieldInfo

        field_info = FieldInfo(
            field_id="PX_LAST",
            field_name="Last Price",
            description="The last traded price",
            data_type="Double",
        )

        assert field_info.field_id == "PX_LAST"
        assert field_info.field_name == "Last Price"
        assert field_info.description == "The last traded price"
        assert field_info.data_type == "Double"


class TestChunkConfig:
    """Tests for ChunkConfig dataclass.

    ChunkConfig holds configuration for chunked Bloomberg requests.
    """

    def test_正常系_デフォルト値で初期化できる(self) -> None:
        """ChunkConfig がデフォルト値で初期化されることを確認。"""
        from market.bloomberg.constants import (
            DEFAULT_CHUNK_SIZE,
            DEFAULT_MAX_RETRIES,
            DEFAULT_RETRY_DELAY,
        )
        from market.bloomberg.types import ChunkConfig

        config = ChunkConfig()

        assert config.chunk_size == DEFAULT_CHUNK_SIZE
        assert config.max_retries == DEFAULT_MAX_RETRIES
        assert config.retry_delay == DEFAULT_RETRY_DELAY

    def test_正常系_カスタム値で初期化できる(self) -> None:
        """ChunkConfig がカスタム値で初期化されることを確認。"""
        from market.bloomberg.types import ChunkConfig

        config = ChunkConfig(chunk_size=100, max_retries=5, retry_delay=1.5)

        assert config.chunk_size == 100
        assert config.max_retries == 5
        assert config.retry_delay == 1.5

    def test_正常系_chunk_sizeが正の整数(self) -> None:
        """chunk_size が正の整数であることを確認。"""
        from market.bloomberg.types import ChunkConfig

        config = ChunkConfig(chunk_size=50)

        assert isinstance(config.chunk_size, int)
        assert config.chunk_size > 0

    def test_正常系_retry_delayが浮動小数点数(self) -> None:
        """retry_delay が float であることを確認。"""
        from market.bloomberg.types import ChunkConfig

        config = ChunkConfig(retry_delay=2.0)

        assert isinstance(config.retry_delay, float)


class TestEarningsInfo:
    """Tests for EarningsInfo dataclass.

    EarningsInfo holds earnings announcement information for a security.
    """

    def test_正常系_必須パラメータで初期化できる(self) -> None:
        """EarningsInfo が必須パラメータで初期化されることを確認。"""
        from datetime import date

        from market.bloomberg.types import EarningsInfo

        info = EarningsInfo(
            security="AAPL US Equity",
            expected_report_dt=date(2024, 10, 31),
            period="Q4 2024",
        )

        assert info.security == "AAPL US Equity"
        assert info.expected_report_dt == date(2024, 10, 31)
        assert info.period == "Q4 2024"

    def test_正常系_異なる銘柄で初期化できる(self) -> None:
        """異なる銘柄でも EarningsInfo が初期化されることを確認。"""
        from datetime import date

        from market.bloomberg.types import EarningsInfo

        info = EarningsInfo(
            security="7203 JP Equity",
            expected_report_dt=date(2024, 11, 1),
            period="FY2024 Q2",
        )

        assert info.security == "7203 JP Equity"
        assert info.period == "FY2024 Q2"

    def test_正常系_securityがstr型(self) -> None:
        """security フィールドが str 型であることを確認。"""
        from datetime import date

        from market.bloomberg.types import EarningsInfo

        info = EarningsInfo(
            security="MSFT US Equity",
            expected_report_dt=date(2024, 7, 30),
            period="Q3 2024",
        )

        assert isinstance(info.security, str)


class TestIdentifierConversionResult:
    """Tests for IdentifierConversionResult dataclass.

    IdentifierConversionResult holds the result of converting a security identifier.
    """

    def test_正常系_必須パラメータで初期化できる(self) -> None:
        """IdentifierConversionResult が必須パラメータで初期化されることを確認。"""
        from datetime import date

        from market.bloomberg.types import IdentifierConversionResult

        result = IdentifierConversionResult(
            original="AAPL US Equity",
            converted="US0378331005",
            date=date(2024, 1, 15),
            status="success",
        )

        assert result.original == "AAPL US Equity"
        assert result.converted == "US0378331005"
        assert result.date == date(2024, 1, 15)
        assert result.status == "success"

    def test_正常系_失敗ステータスで初期化できる(self) -> None:
        """失敗ステータスで IdentifierConversionResult が初期化されることを確認。"""
        from datetime import date

        from market.bloomberg.types import IdentifierConversionResult

        result = IdentifierConversionResult(
            original="INVALID_TICKER",
            converted="",
            date=date(2024, 1, 15),
            status="failed",
        )

        assert result.status == "failed"
        assert result.converted == ""

    def test_正常系_originalがstr型(self) -> None:
        """original フィールドが str 型であることを確認。"""
        from datetime import date

        from market.bloomberg.types import IdentifierConversionResult

        result = IdentifierConversionResult(
            original="7203 JP Equity",
            converted="/sedol/6900643",
            date=date(2024, 1, 15),
            status="success",
        )

        assert isinstance(result.original, str)
        assert isinstance(result.converted, str)
