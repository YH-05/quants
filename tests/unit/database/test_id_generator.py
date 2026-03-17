"""Tests for database.id_generator module."""

from __future__ import annotations

import uuid

import pytest

from database.id_generator import (
    _sha256_prefix,
    generate_author_id,
    generate_claim_id,
    generate_datapoint_id,
    generate_datapoint_id_from_fields,
    generate_entity_id,
    generate_fact_id,
    generate_fiscal_period_id,
    generate_insight_id,
    generate_source_id,
    generate_topic_id,
)


class TestSha256Prefix:
    """Tests for _sha256_prefix helper."""

    def test_正常系_デフォルト長で32文字を返す(self) -> None:
        result = _sha256_prefix("test")
        assert len(result) == 32

    def test_正常系_カスタム長で指定文字数を返す(self) -> None:
        result = _sha256_prefix("test", length=16)
        assert len(result) == 16

    def test_正常系_同じ入力で同じ結果を返す(self) -> None:
        assert _sha256_prefix("hello") == _sha256_prefix("hello")

    def test_正常系_異なる入力で異なる結果を返す(self) -> None:
        assert _sha256_prefix("hello") != _sha256_prefix("world")

    def test_正常系_16進数文字列を返す(self) -> None:
        result = _sha256_prefix("test")
        int(result, 16)  # raises ValueError if not hex


class TestGenerateSourceId:
    """Tests for generate_source_id."""

    def test_正常系_決定論的にUUID5を生成する(self) -> None:
        url = "https://example.com/report.pdf"
        id1 = generate_source_id(url)
        id2 = generate_source_id(url)
        assert id1 == id2

    def test_正常系_UUID形式の36文字を返す(self) -> None:
        result = generate_source_id("https://example.com")
        assert len(result) == 36
        uuid.UUID(result)  # validates format

    def test_正常系_異なるURLで異なるIDを返す(self) -> None:
        id1 = generate_source_id("https://example.com/a")
        id2 = generate_source_id("https://example.com/b")
        assert id1 != id2


class TestGenerateEntityId:
    """Tests for generate_entity_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        id1 = generate_entity_id("Apple", "company")
        id2 = generate_entity_id("Apple", "company")
        assert id1 == id2

    def test_正常系_異なる名前で異なるIDを返す(self) -> None:
        id1 = generate_entity_id("Apple", "company")
        id2 = generate_entity_id("Google", "company")
        assert id1 != id2

    def test_正常系_異なるタイプで異なるIDを返す(self) -> None:
        id1 = generate_entity_id("Apple", "company")
        id2 = generate_entity_id("Apple", "index")
        assert id1 != id2

    def test_正常系_UUID形式を返す(self) -> None:
        result = generate_entity_id("Apple", "company")
        uuid.UUID(result)


class TestGenerateClaimId:
    """Tests for generate_claim_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        content = "S&P 500 will rise 10% in 2026"
        id1 = generate_claim_id(content)
        id2 = generate_claim_id(content)
        assert id1 == id2

    def test_正常系_32文字のハッシュを返す(self) -> None:
        result = generate_claim_id("test claim")
        assert len(result) == 32

    def test_正常系_異なるコンテンツで異なるIDを返す(self) -> None:
        id1 = generate_claim_id("bullish on tech")
        id2 = generate_claim_id("bearish on tech")
        assert id1 != id2


class TestGenerateFactId:
    """Tests for generate_fact_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        content = "Revenue was $100B in Q4"
        id1 = generate_fact_id(content)
        id2 = generate_fact_id(content)
        assert id1 == id2

    def test_正常系_32文字のハッシュを返す(self) -> None:
        result = generate_fact_id("test fact")
        assert len(result) == 32

    def test_正常系_同一コンテンツでもclaim_idと異なるIDを返す(self) -> None:
        content = "Same content for both"
        fact_id = generate_fact_id(content)
        claim_id = generate_claim_id(content)
        assert fact_id != claim_id


class TestGenerateTopicId:
    """Tests for generate_topic_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        id1 = generate_topic_id("AI Semiconductors", "ai")
        id2 = generate_topic_id("AI Semiconductors", "ai")
        assert id1 == id2

    def test_正常系_異なる名前で異なるIDを返す(self) -> None:
        id1 = generate_topic_id("AI", "ai")
        id2 = generate_topic_id("Fed", "macro")
        assert id1 != id2

    def test_正常系_UUID形式を返す(self) -> None:
        result = generate_topic_id("Tech", "sector")
        uuid.UUID(result)


class TestGenerateAuthorId:
    """Tests for generate_author_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        id1 = generate_author_id("Goldman Sachs", "sell_side")
        id2 = generate_author_id("Goldman Sachs", "sell_side")
        assert id1 == id2

    def test_正常系_異なる名前で異なるIDを返す(self) -> None:
        id1 = generate_author_id("GS", "sell_side")
        id2 = generate_author_id("MS", "sell_side")
        assert id1 != id2

    def test_正常系_UUID形式の36文字を返す(self) -> None:
        result = generate_author_id("Test", "person")
        assert len(result) == 36
        uuid.UUID(result)


class TestGenerateDatapointId:
    """Tests for generate_datapoint_id."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        content = "GDP grew 2.5% in Q4"
        id1 = generate_datapoint_id(content)
        id2 = generate_datapoint_id(content)
        assert id1 == id2

    def test_正常系_32文字のハッシュを返す(self) -> None:
        result = generate_datapoint_id("test")
        assert len(result) == 32


class TestGenerateDatapointIdFromFields:
    """Tests for generate_datapoint_id_from_fields."""

    def test_正常系_決定論的にIDを生成する(self) -> None:
        id1 = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
        id2 = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
        assert id1 == id2

    def test_正常系_32文字のハッシュを返す(self) -> None:
        result = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
        assert len(result) == 32

    def test_正常系_異なるフィールドで異なるIDを返す(self) -> None:
        id1 = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
        id2 = generate_datapoint_id_from_fields("abc", "EBITDA", "FY2025")
        assert id1 != id2

    def test_正常系_コロン区切りでアンダースコアとの衝突を防止(self) -> None:
        # "abc_Rev" + "enue" + "FY2025" vs "abc" + "Rev_enue" + "FY2025"
        # would collide with underscore delimiter, but not with colon
        id1 = generate_datapoint_id_from_fields("abc_Rev", "enue", "FY2025")
        id2 = generate_datapoint_id_from_fields("abc", "Rev_enue", "FY2025")
        assert id1 != id2


class TestGenerateFiscalPeriodId:
    """Tests for generate_fiscal_period_id."""

    def test_正常系_ticker_periodlabelの形式を返す(self) -> None:
        result = generate_fiscal_period_id("AAPL", "FY2025")
        assert result == "AAPL_FY2025"

    def test_正常系_四半期の形式を返す(self) -> None:
        result = generate_fiscal_period_id("MSFT", "4Q25")
        assert result == "MSFT_4Q25"

    def test_正常系_半期の形式を返す(self) -> None:
        result = generate_fiscal_period_id("GOOG", "1H26")
        assert result == "GOOG_1H26"


class TestGenerateInsightId:
    """Tests for generate_insight_id."""

    def test_正常系_日付ベースの連番IDを返す(self) -> None:
        result = generate_insight_id("2026-03-17", 1)
        assert result == "ins-2026-03-17-0001"

    def test_正常系_42番目のIDを返す(self) -> None:
        result = generate_insight_id("2026-03-17", 42)
        assert result == "ins-2026-03-17-0042"

    def test_正常系_ゼロ埋め4桁を返す(self) -> None:
        result = generate_insight_id("2026-01-01", 1)
        assert result.endswith("-0001")

    def test_正常系_大きな連番にも対応する(self) -> None:
        result = generate_insight_id("2026-12-31", 9999)
        assert result == "ins-2026-12-31-9999"


class TestIdCollisionPrevention:
    """ID衝突防止の横断的テスト。"""

    def test_正常系_factとclaimは同一コンテンツでも異なるIDを生成(self) -> None:
        content = "Revenue grew 15% YoY"
        assert generate_fact_id(content) != generate_claim_id(content)

    def test_正常系_datapointとclaimは同一コンテンツでも異なるIDを生成(self) -> None:
        content = "Revenue grew 15% YoY"
        assert generate_datapoint_id(content) != generate_fact_id(content)

    def test_正常系_entityとtopicは同一名前でも異なるIDを生成(self) -> None:
        # entity_id uses "entity:" prefix, topic_id uses "topic:" prefix
        entity_id = generate_entity_id("Tech", "sector")
        topic_id = generate_topic_id("Tech", "sector")
        assert entity_id != topic_id

    def test_正常系_authorとentityは同一名前でも異なるIDを生成(self) -> None:
        author_id = generate_author_id("Goldman Sachs", "sell_side")
        entity_id = generate_entity_id("Goldman Sachs", "organization")
        assert author_id != entity_id
