"""Tests for scripts/emit_graph_queue.py mapper functions."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from emit_graph_queue import (
    _empty_queue,
    _infer_period_type,
    _normalise_period_label,
    generate_queue_id,
    map_ai_research,
    map_ca_eval,
    map_dr_industry,
    map_dr_stock,
    map_finance_news,
    map_finance_research,
    map_market_report,
    resolve_category,
)


class TestHelpers:
    """Tests for helper functions."""

    def test_正常系_generate_queue_idがgq_prefixで始まる(self) -> None:
        qid = generate_queue_id()
        assert qid.startswith("gq-")
        # Format: gq-YYYYMMDDHHMMSS-xxxxxxxx
        parts = qid.split("-")
        assert len(parts) == 3
        assert len(parts[2]) == 8  # 4 bytes hex = 8 chars

    def test_正常系_empty_queueが全必須キーを持つ(self) -> None:
        queue = _empty_queue("test-command", "test/path.json")
        required_keys = {
            "schema_version",
            "queue_id",
            "created_at",
            "command_source",
            "input_path",
            "sources",
            "entities",
            "claims",
            "facts",
            "topics",
            "authors",
            "financial_datapoints",
            "fiscal_periods",
            "insights",
            "relations",
        }
        assert required_keys.issubset(set(queue.keys()))
        assert queue["schema_version"] == "1.0"
        assert queue["command_source"] == "test-command"

    def test_正常系_resolve_categoryがテーマを変換する(self) -> None:
        assert resolve_category("index") == "stock"
        assert resolve_category("macro_cnbc") == "macro"
        assert resolve_category("ai_nasdaq") == "ai"
        assert resolve_category("unknown") == "unknown"

    def test_正常系_infer_period_typeが年次を判定(self) -> None:
        assert _infer_period_type("FY2024") == "annual"
        assert _infer_period_type("FY25") == "annual"

    def test_正常系_infer_period_typeが四半期を判定(self) -> None:
        assert _infer_period_type("Q3 2025") == "quarterly"
        assert _infer_period_type("1Q25") == "quarterly"

    def test_正常系_normalise_period_labelがスペースをアンダースコアに変換(
        self,
    ) -> None:
        assert _normalise_period_label("Q3 2025") == "Q3_2025"
        assert _normalise_period_label("FY2024") == "FY2024"


class TestMapFinanceNews:
    """Tests for map_finance_news mapper."""

    def test_正常系_記事からSourceとClaimを生成(self) -> None:
        data: dict[str, Any] = {
            "theme": "index",
            "articles": [
                {
                    "url": "https://example.com/news/1",
                    "title": "S&P 500 hits record",
                    "summary": "S&P 500 reached all-time high today.",
                    "published": "2026-03-17T10:00:00Z",
                    "feed_source": "CNBC",
                },
            ],
        }
        queue = map_finance_news(data)

        assert len(queue["sources"]) == 1
        assert len(queue["claims"]) == 1
        assert len(queue["topics"]) == 1
        assert queue["topics"][0]["category"] == "stock"
        assert len(queue["relations"]["makes_claim"]) == 1
        assert len(queue["relations"]["tagged"]) == 1

    def test_正常系_URL欠落記事をスキップ(self) -> None:
        data: dict[str, Any] = {
            "articles": [
                {"title": "No URL article", "summary": "Test"},
            ],
        }
        queue = map_finance_news(data)
        assert len(queue["sources"]) == 0

    def test_正常系_空記事リストで空キューを返す(self) -> None:
        data: dict[str, Any] = {"articles": []}
        queue = map_finance_news(data)
        assert len(queue["sources"]) == 0
        assert len(queue["claims"]) == 0

    def test_正常系_同一URLで冪等なIDを生成(self) -> None:
        data: dict[str, Any] = {
            "articles": [
                {"url": "https://example.com/a", "title": "A", "summary": "Sum"},
            ],
        }
        q1 = map_finance_news(data)
        q2 = map_finance_news(data)
        assert q1["sources"][0]["id"] == q2["sources"][0]["id"]
        assert q1["claims"][0]["id"] == q2["claims"][0]["id"]


class TestMapAiResearch:
    """Tests for map_ai_research mapper."""

    def test_正常系_記事からEntityとSourceを生成(self) -> None:
        data: dict[str, Any] = {
            "articles": [
                {
                    "url": "https://nvidia.com/blog/1",
                    "title": "NVIDIA AI Update",
                    "summary": "New GPU architecture",
                    "company": "NVIDIA",
                    "category": "ai",
                },
            ],
        }
        queue = map_ai_research(data)

        assert len(queue["sources"]) == 1
        assert len(queue["entities"]) == 1
        assert queue["entities"][0]["entity_type"] == "company"
        assert len(queue["relations"]["about"]) == 1

    def test_正常系_同一企業が重複しない(self) -> None:
        data: dict[str, Any] = {
            "articles": [
                {"url": "https://nvidia.com/1", "title": "A", "company": "NVIDIA"},
                {"url": "https://nvidia.com/2", "title": "B", "company": "NVIDIA"},
            ],
        }
        queue = map_ai_research(data)
        assert len(queue["entities"]) == 1  # deduplicated
        assert len(queue["sources"]) == 2


class TestMapMarketReport:
    """Tests for map_market_report mapper."""

    def test_正常系_インデックスデータからEntityとDataPointを生成(self) -> None:
        data: dict[str, Any] = {
            "report_date": "2026-03-14",
            "indices": [
                {"name": "S&P 500", "close": 5800, "change_pct": 1.5},
            ],
            "summary": "Markets rallied this week.",
        }
        queue = map_market_report(data)

        assert len(queue["sources"]) == 1  # report source
        assert len(queue["entities"]) == 1
        assert queue["entities"][0]["entity_type"] == "index"
        assert len(queue["financial_datapoints"]) >= 1
        assert len(queue["claims"]) == 1  # summary claim


class TestMapDrStock:
    """Tests for map_dr_stock mapper."""

    def test_正常系_株式分析からEntity_DataPoint_FiscalPeriodを生成(self) -> None:
        data: dict[str, Any] = {
            "research_id": "DR_stock_20260213_MCO",
            "ticker": "MCO",
            "company_name": "Moody's Corporation",
            "analyzed_at": "2026-02-13T18:00:00Z",
            "financial_health": {
                "revenue_trend": {
                    "data_points": [
                        {"period": "FY2024", "value": 7088000000, "growth": 19.8},
                        {"period": "FY2023", "value": 5916000000, "growth": 8.2},
                    ],
                    "quarterly_trend": [
                        {"period": "Q3 2025", "revenue": 2009000000},
                    ],
                },
                "profitability": {
                    "operating_margin": 46.9,
                    "net_margin": 29.9,
                    "roe": 54.9,
                    "roa": 13.2,
                    "roic": 25.0,
                },
            },
        }
        queue = map_dr_stock(data)

        # Entity
        assert len(queue["entities"]) == 1
        assert queue["entities"][0]["ticker"] == "MCO"

        # FiscalPeriods: FY2024, FY2023, Q3_2025
        assert len(queue["fiscal_periods"]) == 3

        # DataPoints: revenue(FY2024) + growth(FY2024) + revenue(FY2023) + growth(FY2023)
        #            + quarterly_revenue(Q3_2025)
        #            + 5 profitability metrics
        assert len(queue["financial_datapoints"]) >= 10

        # Relations
        assert len(queue["relations"]["has_datapoint"]) >= 10
        assert len(queue["relations"]["for_period"]) >= 3

    def test_正常系_ticker欠落で空キューを返す(self) -> None:
        data: dict[str, Any] = {"company_name": "Test Corp"}
        queue = map_dr_stock(data)
        assert len(queue["entities"]) == 0

    def test_正常系_決定論的IDを生成(self) -> None:
        data: dict[str, Any] = {
            "research_id": "DR_stock_test",
            "ticker": "TEST",
            "company_name": "Test Corp",
            "financial_health": {
                "revenue_trend": {
                    "data_points": [{"period": "FY2024", "value": 1000}],
                },
            },
        }
        q1 = map_dr_stock(data)
        q2 = map_dr_stock(data)
        assert q1["entities"][0]["id"] == q2["entities"][0]["id"]
        assert q1["fiscal_periods"][0]["id"] == q2["fiscal_periods"][0]["id"]
        assert (
            q1["financial_datapoints"][0]["id"] == q2["financial_datapoints"][0]["id"]
        )


class TestMapCaEval:
    """Tests for map_ca_eval mapper."""

    def test_正常系_CA評価からClaim_Fact_Insightを生成(self) -> None:
        data: dict[str, Any] = {
            "research_id": "CA_eval_20260220-0931_MCO",
            "ticker": "MCO",
            "company_name": "Moody's Corporation",
            "extracted_at": "2026-02-20T09:50:00Z",
            "claims": [
                {
                    "title": "格付け市場の寡占構造",
                    "ca_type": "structural",
                    "description": "MCOとSPGIで格付け市場の各4割を占める",
                    "factual_claims": [
                        "MCOとSPGIで格付け市場の各40%のシェア",
                        "Fitchが2割弱で3位、その他5%",
                    ],
                    "cagr_mechanism": "寡占構造→新規参入なし→既存プレイヤーが市場成長を享受",
                },
            ],
        }
        queue = map_ca_eval(data)

        assert len(queue["claims"]) == 1
        assert len(queue["facts"]) == 2
        assert len(queue["insights"]) == 1
        assert len(queue["entities"]) == 1
        assert queue["entities"][0]["ticker"] == "MCO"

        # Relations
        assert len(queue["relations"]["makes_claim"]) == 1
        assert len(queue["relations"]["supported_by"]) == 2
        assert len(queue["relations"]["about"]) >= 2  # source→entity + claim→entity

    def test_正常系_ticker欠落で空キューを返す(self) -> None:
        data: dict[str, Any] = {"company_name": "Test Corp", "claims": []}
        queue = map_ca_eval(data)
        assert len(queue["claims"]) == 0


class TestMapDrIndustry:
    """Tests for map_dr_industry mapper."""

    def test_正常系_業界分析からEntityとClaimを生成(self) -> None:
        data: dict[str, Any] = {
            "research_id": "DR_industry_20260301_Tech",
            "sector": "Information Technology",
            "analyzed_at": "2026-03-01T10:00:00Z",
            "companies": [
                {"name": "Apple", "ticker": "AAPL"},
                {"name": "Microsoft", "ticker": "MSFT"},
            ],
            "claims": [
                {
                    "title": "AI投資加速",
                    "description": "大手テック企業がAI投資を大幅増額",
                    "factual_claims": ["2025年のAI関連設備投資は前年比40%増"],
                },
            ],
            "summary": "テクノロジーセクターはAI投資主導で成長継続",
        }
        queue = map_dr_industry(data)

        # Entities: sector + 2 companies
        assert len(queue["entities"]) == 3
        assert any(e["entity_type"] == "sector" for e in queue["entities"])

        # Claims: 1 claim + 1 summary
        assert len(queue["claims"]) == 2
        assert len(queue["facts"]) == 1

    def test_正常系_sector欠落で空キューを返す(self) -> None:
        data: dict[str, Any] = {"companies": []}
        queue = map_dr_industry(data)
        assert len(queue["entities"]) == 0


class TestMapFinanceResearch:
    """Tests for map_finance_research mapper."""

    def test_正常系_リサーチからSourceとClaimを生成(self) -> None:
        data: dict[str, Any] = {
            "research_id": "research_20260317",
            "topic": "Fed Rate Decision Impact",
            "sources": [
                {"url": "https://fed.gov/statement", "title": "Fed Statement"},
            ],
            "findings": [
                {
                    "content": "Fed likely to cut rates by 25bp in June",
                    "evidence_urls": ["https://fed.gov/statement"],
                },
            ],
            "key_points": [
                "Bond yields expected to decline",
            ],
        }
        queue = map_finance_research(data)

        # Sources: research itself + 1 reference
        assert len(queue["sources"]) == 2
        # Claims: 1 finding + 1 key point
        assert len(queue["claims"]) == 2
        # SUPPORTED_BY: finding → fed statement
        assert len(queue["relations"]["supported_by"]) == 1


class TestGraphQueueStructure:
    """Graph-queue JSON 構造の横断的テスト。"""

    def test_正常系_全mapperがschema_versionを含む(self) -> None:
        mappers = {
            "finance-news": map_finance_news,
            "ai-research": map_ai_research,
            "market-report": map_market_report,
            "dr-stock": map_dr_stock,
            "ca-eval": map_ca_eval,
            "dr-industry": map_dr_industry,
            "finance-research": map_finance_research,
        }
        for name, mapper in mappers.items():
            queue = mapper({})
            assert "schema_version" in queue, f"{name} missing schema_version"
            assert queue["schema_version"] == "1.0", f"{name} wrong schema_version"

    def test_正常系_全mapperがrelationsを含む(self) -> None:
        mappers = [
            map_finance_news,
            map_ai_research,
            map_market_report,
            map_dr_stock,
            map_ca_eval,
            map_dr_industry,
            map_finance_research,
        ]
        expected_relations = {
            "tagged",
            "makes_claim",
            "states_fact",
            "about",
            "relates_to",
            "has_datapoint",
            "for_period",
            "supported_by",
            "authored_by",
        }
        for mapper in mappers:
            queue = mapper({})
            assert "relations" in queue
            assert expected_relations.issubset(set(queue["relations"].keys()))
