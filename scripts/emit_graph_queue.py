#!/usr/bin/env python3
"""Emit graph-queue JSON from various command outputs.

Converts outputs from 7 workflow commands into a unified graph-queue
JSON format suitable for Neo4j ingestion.  Each mapper function
receives parsed JSON data and returns a complete graph-queue dict
with deterministic IDs.

Supported commands
------------------
- finance-news-workflow
- ai-research-collect
- generate-market-report
- dr-stock
- ca-eval
- dr-industry
- finance-research

Usage
-----
::

    # Basic usage
    uv run python scripts/emit_graph_queue.py --command dr-stock \\
        --input research/DR_stock_20260213_MCO/03_analysis/stock-analysis.json

    # Cleanup files older than 7 days
    uv run python scripts/emit_graph_queue.py --cleanup

    # Custom output directory
    uv run python scripts/emit_graph_queue.py --command ca-eval \\
        --input analyst/research/CA_eval_20260220-0931_MCO/02_claims/claims.json \\
        --output-dir .tmp/graph-queue/ca-eval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils_core.logging import get_logger

from database.id_generator import (
    generate_author_id,
    generate_claim_id,
    generate_datapoint_id_from_fields,
    generate_entity_id,
    generate_fact_id,
    generate_fiscal_period_id,
    generate_insight_id,
    generate_source_id,
    generate_topic_id,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
DEFAULT_OUTPUT_BASE = Path(".tmp/graph-queue")
DEFAULT_MAX_AGE_DAYS = 7

THEME_TO_CATEGORY: dict[str, str] = {
    "index": "stock",
    "stock": "stock",
    "sector": "sector",
    "macro_cnbc": "macro",
    "macro_other": "macro",
    "ai_cnbc": "ai",
    "ai_nasdaq": "ai",
    "ai_tech": "ai",
    "finance_cnbc": "finance",
    "finance_nasdaq": "finance",
    "finance_other": "finance",
}

type MapperFn = Callable[[dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_queue_id() -> str:
    """Generate a unique queue ID with timestamp and random suffix.

    Returns
    -------
    str
        Queue ID in format ``gq-{YYYYMMDDHHMMSS}-{rand8hex}``.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand8 = secrets.token_hex(4)
    return f"gq-{timestamp}-{rand8}"


def _empty_queue(
    command_source: str,
    input_path: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create an empty graph-queue structure.

    Parameters
    ----------
    command_source : str
        Name of the command that produced the data.
    input_path : str
        Path to the input file.
    now : datetime, optional
        Timestamp to use for ``created_at`` (default: current UTC time).

    Returns
    -------
    dict[str, Any]
        Empty graph-queue dict with all required keys initialised.
    """
    now = now or datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "queue_id": generate_queue_id(),
        "created_at": now.isoformat(),
        "command_source": command_source,
        "input_path": input_path,
        "sources": [],
        "entities": [],
        "claims": [],
        "facts": [],
        "topics": [],
        "authors": [],
        "financial_datapoints": [],
        "fiscal_periods": [],
        "insights": [],
        "relations": {
            "tagged": [],
            "makes_claim": [],
            "states_fact": [],
            "about": [],
            "relates_to": [],
            "has_datapoint": [],
            "for_period": [],
            "supported_by": [],
            "authored_by": [],
        },
    }


def _infer_period_type(period_label: str) -> str:
    """Infer the period type from a period label string.

    Parameters
    ----------
    period_label : str
        Period label such as ``"FY2024"``, ``"Q3 2025"``, ``"1H26"``.

    Returns
    -------
    str
        One of ``"annual"``, ``"quarterly"``, ``"semi_annual"``, or ``"unknown"``.
    """
    label_upper = period_label.upper().strip()
    if label_upper.startswith("FY"):
        return "annual"
    if re.match(r"Q\d", label_upper):
        return "quarterly"
    if re.match(r"\dH", label_upper):
        return "semi_annual"
    if re.match(r"\d{1,2}Q", label_upper):
        return "quarterly"
    return "unknown"


def resolve_category(theme_key: str) -> str:
    """Resolve a theme key to a KG topic category.

    Parameters
    ----------
    theme_key : str
        Theme key from news batch (e.g. ``"index"``, ``"macro_cnbc"``).

    Returns
    -------
    str
        Category string (e.g. ``"stock"``, ``"macro"``).
    """
    return THEME_TO_CATEGORY.get(theme_key, theme_key)


def _sha256_short(text: str, length: int = 32) -> str:
    """Return the first *length* hex characters of SHA-256 of *text*.

    Used internally for generating source hashes to pass to
    :func:`generate_datapoint_id_from_fields`.

    Parameters
    ----------
    text : str
        Input text to hash.
    length : int, optional
        Number of hex characters to return (default 32).

    Returns
    -------
    str
        Hex prefix of the SHA-256 digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _normalise_period_label(raw: str) -> str:
    """Normalise a period label for fiscal period ID generation.

    Converts formats like ``"Q3 2025"`` to ``"Q3_2025"`` so the
    resulting fiscal period ID is clean.

    Parameters
    ----------
    raw : str
        Raw period label (e.g. ``"Q3 2025"``, ``"FY2024"``).

    Returns
    -------
    str
        Normalised period label with spaces replaced by underscores.
    """
    return raw.strip().replace(" ", "_")


# ---------------------------------------------------------------------------
# Wave 2 Mappers (lighter)
# ---------------------------------------------------------------------------


def map_finance_news(data: dict[str, Any]) -> dict[str, Any]:
    """Map finance news batch articles to graph-queue format.

    Input: Array of articles from ``.tmp/news-batches/{theme}_articles.json``.
    Each article has fields: url, title, summary, published, feed_source.

    Creates: Source + Claim (from summary) + Topic (category-based)
    Relations: Source -[MAKES_CLAIM]-> Claim, Source -[TAGGED]-> Topic

    Parameters
    ----------
    data : dict[str, Any]
        Parsed JSON with keys ``articles`` (list) and optional ``theme``
        (str, defaults to ``"stock"``).

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("finance-news-workflow", input_path)

    articles: list[dict[str, Any]] = data.get("articles", [])
    theme_key: str = data.get("theme", "stock")
    category = resolve_category(theme_key)

    if not articles:
        logger.warning("No articles found in finance-news input")
        return queue

    # Create the category-level Topic node
    topic_name = category.capitalize()
    topic_id = generate_topic_id(topic_name, category)
    queue["topics"].append({
        "id": topic_id,
        "name": topic_name,
        "category": category,
    })

    for article in articles:
        url = article.get("url") or article.get("link", "")
        title = article.get("title", "")
        summary = article.get("summary", "")
        published = article.get("published", "")
        feed_source = article.get("feed_source", "")

        if not url:
            logger.warning("Article missing URL, skipping", title=title)
            continue

        # Source node
        source_id = generate_source_id(url)
        queue["sources"].append({
            "id": source_id,
            "url": url,
            "title": title,
            "published": published,
            "feed_source": feed_source,
            "source_type": "news_article",
        })

        # Claim node from summary
        if summary:
            claim_id = generate_claim_id(summary)
            queue["claims"].append({
                "id": claim_id,
                "content": summary,
                "source_url": url,
                "claim_type": "news_summary",
            })
            queue["relations"]["makes_claim"].append({
                "from_id": source_id,
                "to_id": claim_id,
            })

        # Tag source to topic
        queue["relations"]["tagged"].append({
            "from_id": source_id,
            "to_id": topic_id,
        })

    logger.info(
        "Mapped finance-news articles",
        article_count=len(articles),
        source_count=len(queue["sources"]),
        claim_count=len(queue["claims"]),
    )
    return queue


def map_ai_research(data: dict[str, Any]) -> dict[str, Any]:
    """Map AI research articles to graph-queue format.

    Input: AI research articles from ``.tmp/ai-research-batches/``.
    Each article has fields: url, title, summary, company, category.

    Creates: Entity (company) + Source
    Relations: Source -[ABOUT]-> Entity

    Parameters
    ----------
    data : dict[str, Any]
        Parsed JSON with key ``articles`` (list of article dicts).

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("ai-research-collect", input_path)

    articles: list[dict[str, Any]] = data.get("articles", [])

    if not articles:
        logger.warning("No articles found in ai-research input")
        return queue

    # Track entities to avoid duplicates within this batch
    seen_entities: dict[str, str] = {}

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")
        summary = article.get("summary", "")
        company = article.get("company", "")
        category = article.get("category", "ai")

        if not url:
            logger.warning("AI research article missing URL, skipping", title=title)
            continue

        # Source node
        source_id = generate_source_id(url)
        queue["sources"].append({
            "id": source_id,
            "url": url,
            "title": title,
            "summary": summary,
            "source_type": "ai_research_article",
            "category": category,
        })

        # Entity node (company)
        if company:
            entity_key = f"{company}:company"
            if entity_key not in seen_entities:
                entity_id = generate_entity_id(company, "company")
                seen_entities[entity_key] = entity_id
                queue["entities"].append({
                    "id": entity_id,
                    "name": company,
                    "entity_type": "company",
                })
            else:
                entity_id = seen_entities[entity_key]

            queue["relations"]["about"].append({
                "from_id": source_id,
                "to_id": entity_id,
            })

    logger.info(
        "Mapped ai-research articles",
        article_count=len(articles),
        source_count=len(queue["sources"]),
        entity_count=len(queue["entities"]),
    )
    return queue


def map_market_report(data: dict[str, Any]) -> dict[str, Any]:
    """Map weekly market report data to graph-queue format.

    Input: Weekly market report data from ``data/{date}/`` containing
    indices, sectors, MAG7 stocks with prices/changes.

    Creates: Source + Entity + FinancialDataPoint + Claim
    Relations: Entity -[HAS_DATAPOINT]-> FinancialDataPoint,
               Source -[MAKES_CLAIM]-> Claim,
               Source -[ABOUT]-> Entity

    Parameters
    ----------
    data : dict[str, Any]
        Parsed JSON with keys such as ``report_date``, ``indices``,
        ``sectors``, ``stocks``, and optional ``summary``.

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("generate-market-report", input_path)

    report_date = data.get("report_date", "")
    report_url = data.get("url", f"market-report://{report_date}")

    # Source node for the report itself
    source_id = generate_source_id(report_url)
    queue["sources"].append({
        "id": source_id,
        "url": report_url,
        "title": f"Weekly Market Report {report_date}",
        "published": report_date,
        "source_type": "market_report",
    })

    seen_entities: dict[str, str] = {}
    source_hash = _sha256_short(report_url)

    def _process_market_item(
        name: str,
        entity_type: str,
        metrics: dict[str, Any],
        period: str,
    ) -> None:
        """Create Entity + FinancialDataPoint nodes for a market item."""
        entity_key = f"{name}:{entity_type}"
        if entity_key not in seen_entities:
            entity_id = generate_entity_id(name, entity_type)
            seen_entities[entity_key] = entity_id
            queue["entities"].append({
                "id": entity_id,
                "name": name,
                "entity_type": entity_type,
            })
        else:
            entity_id = seen_entities[entity_key]

        queue["relations"]["about"].append({
            "from_id": source_id,
            "to_id": entity_id,
        })

        for metric_name, value in metrics.items():
            if value is None:
                continue
            dp_id = generate_datapoint_id_from_fields(
                source_hash, metric_name, f"{name}_{period}"
            )
            queue["financial_datapoints"].append({
                "id": dp_id,
                "metric": metric_name,
                "value": value,
                "period": period,
                "entity_name": name,
            })
            queue["relations"]["has_datapoint"].append({
                "from_id": entity_id,
                "to_id": dp_id,
            })

    # Process indices
    for index_data in data.get("indices", []):
        name = index_data.get("name", "")
        if not name:
            continue
        metrics = {
            k: v
            for k, v in index_data.items()
            if k not in {"name", "ticker"} and v is not None
        }
        _process_market_item(name, "index", metrics, report_date)

    # Process sectors
    for sector_data in data.get("sectors", []):
        name = sector_data.get("name", sector_data.get("sector", ""))
        if not name:
            continue
        metrics = {
            k: v
            for k, v in sector_data.items()
            if k not in {"name", "sector"} and v is not None
        }
        _process_market_item(name, "sector", metrics, report_date)

    # Process stocks (MAG7, etc.)
    for stock_data in data.get("stocks", []):
        name = stock_data.get("name", stock_data.get("ticker", ""))
        if not name:
            continue
        metrics = {
            k: v
            for k, v in stock_data.items()
            if k not in {"name", "ticker"} and v is not None
        }
        _process_market_item(name, "company", metrics, report_date)

    # Summary claim
    summary = data.get("summary", "")
    if summary:
        claim_id = generate_claim_id(summary)
        queue["claims"].append({
            "id": claim_id,
            "content": summary,
            "claim_type": "market_report_summary",
        })
        queue["relations"]["makes_claim"].append({
            "from_id": source_id,
            "to_id": claim_id,
        })

    logger.info(
        "Mapped market-report data",
        entity_count=len(queue["entities"]),
        datapoint_count=len(queue["financial_datapoints"]),
    )
    return queue


# ---------------------------------------------------------------------------
# Wave 3 Mappers (richer)
# ---------------------------------------------------------------------------


def map_dr_stock(data: dict[str, Any]) -> dict[str, Any]:
    """Map deep-research stock analysis to graph-queue format.

    Input: Comprehensive stock analysis JSON from
    ``research/DR_stock_*/03_analysis/stock-analysis.json``.

    Creates: Entity + FinancialDataPoint + FiscalPeriod + Claim + Fact
    Relations: Entity -[HAS_DATAPOINT]-> FinancialDataPoint,
               FinancialDataPoint -[FOR_PERIOD]-> FiscalPeriod,
               Entity -[STATES_FACT]-> Fact

    Parameters
    ----------
    data : dict[str, Any]
        Parsed stock analysis JSON with ``ticker``, ``company_name``,
        ``financial_health``, ``valuation``, etc.

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("dr-stock", input_path)

    research_id = data.get("research_id", "")
    ticker = data.get("ticker", "")
    company_name = data.get("company_name", "")

    if not ticker:
        logger.error("dr-stock data missing ticker")
        return queue

    # Source node for the research report
    source_url = f"research://{research_id}"
    source_id = generate_source_id(source_url)
    source_hash = _sha256_short(source_url)
    queue["sources"].append({
        "id": source_id,
        "url": source_url,
        "title": f"Deep Research: {company_name} ({ticker})",
        "published": data.get("analyzed_at", ""),
        "source_type": "deep_research_stock",
        "research_id": research_id,
    })

    # Entity node for the company
    entity_id = generate_entity_id(company_name, "company")
    queue["entities"].append({
        "id": entity_id,
        "name": company_name,
        "entity_type": "company",
        "ticker": ticker,
    })
    queue["relations"]["about"].append({
        "from_id": source_id,
        "to_id": entity_id,
    })

    financial_health = data.get("financial_health", {})

    # --- Revenue data points ---
    revenue_trend = financial_health.get("revenue_trend", {})
    for dp in revenue_trend.get("data_points", []):
        period_label = dp.get("period", "")
        value = dp.get("value")
        if not period_label or value is None:
            continue

        normalised = _normalise_period_label(period_label)
        fp_id = generate_fiscal_period_id(ticker, normalised)
        period_type = _infer_period_type(period_label)

        # FiscalPeriod node
        queue["fiscal_periods"].append({
            "id": fp_id,
            "ticker": ticker,
            "period_label": normalised,
            "period_type": period_type,
        })

        # Revenue FinancialDataPoint
        dp_id = generate_datapoint_id_from_fields(source_hash, "revenue", normalised)
        queue["financial_datapoints"].append({
            "id": dp_id,
            "metric": "revenue",
            "value": value,
            "period": normalised,
            "unit": "USD",
        })
        queue["relations"]["has_datapoint"].append({
            "from_id": entity_id,
            "to_id": dp_id,
        })
        queue["relations"]["for_period"].append({
            "from_id": dp_id,
            "to_id": fp_id,
        })

        # Revenue growth as a separate datapoint
        growth = dp.get("growth")
        if growth is not None:
            growth_dp_id = generate_datapoint_id_from_fields(
                source_hash, "revenue_growth_pct", normalised
            )
            queue["financial_datapoints"].append({
                "id": growth_dp_id,
                "metric": "revenue_growth_pct",
                "value": growth,
                "period": normalised,
                "unit": "percent",
            })
            queue["relations"]["has_datapoint"].append({
                "from_id": entity_id,
                "to_id": growth_dp_id,
            })
            queue["relations"]["for_period"].append({
                "from_id": growth_dp_id,
                "to_id": fp_id,
            })

    # --- Quarterly revenue data points ---
    for qdp in revenue_trend.get("quarterly_trend", []):
        period_label = qdp.get("period", "")
        revenue_val = qdp.get("revenue")
        if not period_label or revenue_val is None:
            continue

        normalised = _normalise_period_label(period_label)
        fp_id = generate_fiscal_period_id(ticker, normalised)

        queue["fiscal_periods"].append({
            "id": fp_id,
            "ticker": ticker,
            "period_label": normalised,
            "period_type": "quarterly",
        })

        dp_id = generate_datapoint_id_from_fields(
            source_hash, "quarterly_revenue", normalised
        )
        queue["financial_datapoints"].append({
            "id": dp_id,
            "metric": "quarterly_revenue",
            "value": revenue_val,
            "period": normalised,
            "unit": "USD",
        })
        queue["relations"]["has_datapoint"].append({
            "from_id": entity_id,
            "to_id": dp_id,
        })
        queue["relations"]["for_period"].append({
            "from_id": dp_id,
            "to_id": fp_id,
        })

    # --- Profitability metrics ---
    profitability = financial_health.get("profitability", {})
    profit_metrics = {
        "operating_margin": profitability.get("operating_margin"),
        "net_margin": profitability.get("net_margin"),
        "roe": profitability.get("roe"),
        "roa": profitability.get("roa"),
        "roic": profitability.get("roic"),
    }
    for metric_name, metric_val in profit_metrics.items():
        if metric_val is None:
            continue
        dp_id = generate_datapoint_id_from_fields(
            source_hash, metric_name, "latest"
        )
        queue["financial_datapoints"].append({
            "id": dp_id,
            "metric": metric_name,
            "value": metric_val,
            "period": "latest",
            "unit": "percent",
        })
        queue["relations"]["has_datapoint"].append({
            "from_id": entity_id,
            "to_id": dp_id,
        })

    # --- Balance sheet metrics ---
    balance_sheet = financial_health.get("balance_sheet", {})
    bs_metrics = {
        "debt_to_equity": balance_sheet.get("debt_to_equity"),
        "current_ratio": balance_sheet.get("current_ratio"),
        "interest_coverage": balance_sheet.get("interest_coverage"),
    }
    for metric_name, metric_val in bs_metrics.items():
        if metric_val is None:
            continue
        dp_id = generate_datapoint_id_from_fields(
            source_hash, metric_name, "latest"
        )
        queue["financial_datapoints"].append({
            "id": dp_id,
            "metric": metric_name,
            "value": metric_val,
            "period": "latest",
            "unit": "ratio",
        })
        queue["relations"]["has_datapoint"].append({
            "from_id": entity_id,
            "to_id": dp_id,
        })

    # --- Cash flow metrics ---
    cash_flow = financial_health.get("cash_flow", {})
    cf_metrics = {
        "fcf_ttm": cash_flow.get("fcf_ttm"),
        "fcf_margin": cash_flow.get("fcf_margin"),
    }
    for metric_name, metric_val in cf_metrics.items():
        if metric_val is None:
            continue
        unit = "USD" if "margin" not in metric_name else "percent"
        dp_id = generate_datapoint_id_from_fields(
            source_hash, metric_name, "ttm"
        )
        queue["financial_datapoints"].append({
            "id": dp_id,
            "metric": metric_name,
            "value": metric_val,
            "period": "ttm",
            "unit": unit,
        })
        queue["relations"]["has_datapoint"].append({
            "from_id": entity_id,
            "to_id": dp_id,
        })

    # --- Valuation as Claims ---
    valuation = data.get("valuation", {})
    dcf = valuation.get("absolute", {}).get("dcf_estimate", {})
    if dcf:
        intrinsic = dcf.get("intrinsic_value")
        notes = dcf.get("notes", "")
        if intrinsic is not None:
            claim_text = (
                f"{company_name} ({ticker}) DCF intrinsic value: "
                f"${intrinsic}. {notes}"
            )
            claim_id = generate_claim_id(claim_text)
            queue["claims"].append({
                "id": claim_id,
                "content": claim_text,
                "claim_type": "valuation_dcf",
                "ticker": ticker,
            })
            queue["relations"]["makes_claim"].append({
                "from_id": source_id,
                "to_id": claim_id,
            })

    # --- Overall assessment as Fact ---
    overall_score = financial_health.get("overall_score")
    confidence = financial_health.get("confidence")
    if overall_score is not None:
        fact_text = (
            f"{company_name} ({ticker}) financial health score: "
            f"{overall_score}/10 (confidence: {confidence})"
        )
        fact_id = generate_fact_id(fact_text)
        queue["facts"].append({
            "id": fact_id,
            "content": fact_text,
            "fact_type": "financial_health_score",
            "ticker": ticker,
        })
        queue["relations"]["states_fact"].append({
            "from_id": entity_id,
            "to_id": fact_id,
        })

    logger.info(
        "Mapped dr-stock data",
        ticker=ticker,
        datapoint_count=len(queue["financial_datapoints"]),
        period_count=len(queue["fiscal_periods"]),
        claim_count=len(queue["claims"]),
        fact_count=len(queue["facts"]),
    )
    return queue


def map_ca_eval(data: dict[str, Any]) -> dict[str, Any]:
    """Map competitive advantage evaluation to graph-queue format.

    Input: Claims JSON from
    ``analyst/research/CA_eval_*/02_claims/claims.json``.

    Creates: Claim + Fact + Insight + Entity
    Relations: Claim -[SUPPORTED_BY]-> Fact,
               Source -[MAKES_CLAIM]-> Claim,
               Claim -[ABOUT]-> Entity

    Parameters
    ----------
    data : dict[str, Any]
        Parsed claims JSON with ``ticker``, ``company_name``, ``claims`` list.

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("ca-eval", input_path)

    research_id = data.get("research_id", "")
    ticker = data.get("ticker", "")
    company_name = data.get("company_name", "")
    extracted_at = data.get("extracted_at", "")

    if not ticker:
        logger.error("ca-eval data missing ticker")
        return queue

    # Source node for the CA evaluation
    source_url = f"ca-eval://{research_id}"
    source_id = generate_source_id(source_url)
    queue["sources"].append({
        "id": source_id,
        "url": source_url,
        "title": f"Competitive Advantage Evaluation: {company_name} ({ticker})",
        "published": extracted_at,
        "source_type": "ca_evaluation",
        "research_id": research_id,
    })

    # Entity node for the company
    entity_id = generate_entity_id(company_name, "company")
    queue["entities"].append({
        "id": entity_id,
        "name": company_name,
        "entity_type": "company",
        "ticker": ticker,
    })
    queue["relations"]["about"].append({
        "from_id": source_id,
        "to_id": entity_id,
    })

    # Extract date from research_id for insight IDs
    date_match = re.search(r"(\d{8})", research_id)
    date_str = ""
    if date_match:
        raw_date = date_match.group(1)
        date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    claims_list: list[dict[str, Any]] = data.get("claims", [])
    insight_seq = 0

    for claim_data in claims_list:
        title = claim_data.get("title", "")
        description = claim_data.get("description", "")
        ca_type = claim_data.get("ca_type", "")
        factual_claims: list[str] = claim_data.get("factual_claims", [])
        cagr_mechanism = claim_data.get("cagr_mechanism", "")
        confidence_data = claim_data.get("confidence", {})

        # Claim node
        claim_content = f"[{ticker}] {title}: {description}"
        claim_id = generate_claim_id(claim_content)
        queue["claims"].append({
            "id": claim_id,
            "content": claim_content,
            "claim_type": f"competitive_advantage_{ca_type}",
            "ticker": ticker,
            "ca_type": ca_type,
            "ca_score": confidence_data.get("ca_score"),
            "ca_label": confidence_data.get("label"),
        })
        queue["relations"]["makes_claim"].append({
            "from_id": source_id,
            "to_id": claim_id,
        })
        queue["relations"]["about"].append({
            "from_id": claim_id,
            "to_id": entity_id,
        })

        # Fact nodes from factual_claims
        for fact_text in factual_claims:
            if not fact_text:
                continue
            fact_id = generate_fact_id(fact_text)
            queue["facts"].append({
                "id": fact_id,
                "content": fact_text,
                "fact_type": "competitive_advantage_evidence",
                "ticker": ticker,
            })
            queue["relations"]["supported_by"].append({
                "from_id": claim_id,
                "to_id": fact_id,
            })
            queue["relations"]["states_fact"].append({
                "from_id": entity_id,
                "to_id": fact_id,
            })

        # Insight node from CAGR mechanism
        if cagr_mechanism and date_str:
            insight_seq += 1
            insight_id = generate_insight_id(date_str, insight_seq)
            queue["insights"].append({
                "id": insight_id,
                "content": cagr_mechanism,
                "insight_type": "cagr_mechanism",
                "ticker": ticker,
                "date": date_str,
            })
            queue["relations"]["relates_to"].append({
                "from_id": claim_id,
                "to_id": insight_id,
            })

    logger.info(
        "Mapped ca-eval data",
        ticker=ticker,
        claim_count=len(queue["claims"]),
        fact_count=len(queue["facts"]),
        insight_count=len(queue["insights"]),
    )
    return queue


def map_dr_industry(data: dict[str, Any]) -> dict[str, Any]:
    """Map deep-research industry/sector analysis to graph-queue format.

    Input: Sector analysis data from ``research/DR_industry_*/``.

    Creates: Entity (sector + companies) + Claim + Fact
    Relations: Source -[MAKES_CLAIM]-> Claim,
               Claim -[SUPPORTED_BY]-> Fact,
               Source -[ABOUT]-> Entity

    Parameters
    ----------
    data : dict[str, Any]
        Parsed industry analysis JSON with ``research_id``, ``sector``,
        ``companies`` list, ``claims`` list, etc.

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("dr-industry", input_path)

    research_id = data.get("research_id", "")
    sector_name = data.get("sector", data.get("industry", ""))
    analyzed_at = data.get("analyzed_at", "")

    if not sector_name:
        logger.error("dr-industry data missing sector name")
        return queue

    # Source node
    source_url = f"research://{research_id}"
    source_id = generate_source_id(source_url)
    queue["sources"].append({
        "id": source_id,
        "url": source_url,
        "title": f"Industry Research: {sector_name}",
        "published": analyzed_at,
        "source_type": "deep_research_industry",
        "research_id": research_id,
    })

    # Sector entity
    sector_entity_id = generate_entity_id(sector_name, "sector")
    queue["entities"].append({
        "id": sector_entity_id,
        "name": sector_name,
        "entity_type": "sector",
    })
    queue["relations"]["about"].append({
        "from_id": source_id,
        "to_id": sector_entity_id,
    })

    seen_entities: dict[str, str] = {f"{sector_name}:sector": sector_entity_id}

    # Company entities
    for company in data.get("companies", []):
        name = company.get("name", company.get("company_name", ""))
        ticker = company.get("ticker", "")
        if not name:
            continue

        entity_key = f"{name}:company"
        if entity_key not in seen_entities:
            entity_id = generate_entity_id(name, "company")
            seen_entities[entity_key] = entity_id
            entity_node: dict[str, Any] = {
                "id": entity_id,
                "name": name,
                "entity_type": "company",
            }
            if ticker:
                entity_node["ticker"] = ticker
            queue["entities"].append(entity_node)

            # Company relates_to sector
            queue["relations"]["relates_to"].append({
                "from_id": entity_id,
                "to_id": sector_entity_id,
            })

    # Claims
    for claim_data in data.get("claims", []):
        title = claim_data.get("title", "")
        description = claim_data.get("description", "")
        claim_content = f"[{sector_name}] {title}: {description}" if title else description

        if not claim_content.strip():
            continue

        claim_id = generate_claim_id(claim_content)
        queue["claims"].append({
            "id": claim_id,
            "content": claim_content,
            "claim_type": "industry_analysis",
            "sector": sector_name,
        })
        queue["relations"]["makes_claim"].append({
            "from_id": source_id,
            "to_id": claim_id,
        })

        # Facts from factual_claims
        for fact_text in claim_data.get("factual_claims", []):
            if not fact_text:
                continue
            fact_id = generate_fact_id(fact_text)
            queue["facts"].append({
                "id": fact_id,
                "content": fact_text,
                "fact_type": "industry_evidence",
            })
            queue["relations"]["supported_by"].append({
                "from_id": claim_id,
                "to_id": fact_id,
            })

    # Top-level summary/findings as claims
    summary = data.get("summary", "")
    if summary:
        claim_id = generate_claim_id(summary)
        queue["claims"].append({
            "id": claim_id,
            "content": summary,
            "claim_type": "industry_summary",
            "sector": sector_name,
        })
        queue["relations"]["makes_claim"].append({
            "from_id": source_id,
            "to_id": claim_id,
        })

    logger.info(
        "Mapped dr-industry data",
        sector=sector_name,
        entity_count=len(queue["entities"]),
        claim_count=len(queue["claims"]),
        fact_count=len(queue["facts"]),
    )
    return queue


def map_finance_research(data: dict[str, Any]) -> dict[str, Any]:
    """Map article research data to graph-queue format.

    Input: Research data from ``articles/*/01_research/`` used for
    finance article writing.

    Creates: Source + Claim
    Relations: Source -[MAKES_CLAIM]-> Claim,
               Claim -[SUPPORTED_BY]-> Source (when evidence links exist)

    Parameters
    ----------
    data : dict[str, Any]
        Parsed research JSON with ``research_id``, ``topic``, ``sources``
        list, ``findings`` list, etc.

    Returns
    -------
    dict[str, Any]
        Complete graph-queue dict.
    """
    input_path = data.get("_input_path", "")
    queue = _empty_queue("finance-research", input_path)

    research_id = data.get("research_id", "")
    topic = data.get("topic", data.get("title", ""))
    researched_at = data.get("researched_at", data.get("created_at", ""))

    # Source node for the research itself
    research_url = f"finance-research://{research_id}"
    research_source_id = generate_source_id(research_url)
    queue["sources"].append({
        "id": research_source_id,
        "url": research_url,
        "title": f"Finance Research: {topic}",
        "published": researched_at,
        "source_type": "finance_research",
        "research_id": research_id,
    })

    # Referenced sources
    source_id_map: dict[str, str] = {}
    for src in data.get("sources", []):
        url = src.get("url", "")
        title = src.get("title", "")
        if not url:
            continue
        src_id = generate_source_id(url)
        source_id_map[url] = src_id
        queue["sources"].append({
            "id": src_id,
            "url": url,
            "title": title,
            "source_type": "reference",
        })

    # Findings / claims
    for finding in data.get("findings", []):
        content = finding.get("content", finding.get("summary", ""))
        if not content:
            continue

        claim_id = generate_claim_id(content)
        queue["claims"].append({
            "id": claim_id,
            "content": content,
            "claim_type": "research_finding",
            "topic": topic,
        })
        queue["relations"]["makes_claim"].append({
            "from_id": research_source_id,
            "to_id": claim_id,
        })

        # Link claim to supporting sources
        evidence_urls: list[str] = finding.get("evidence_urls", [])
        for ev_url in evidence_urls:
            if ev_url in source_id_map:
                queue["relations"]["supported_by"].append({
                    "from_id": claim_id,
                    "to_id": source_id_map[ev_url],
                })

    # Top-level claims/key_points
    for point in data.get("key_points", []):
        if isinstance(point, str):
            point_text = point
        elif isinstance(point, dict):
            point_text = point.get("content", point.get("text", ""))
        else:
            continue
        if not point_text:
            continue

        claim_id = generate_claim_id(point_text)
        queue["claims"].append({
            "id": claim_id,
            "content": point_text,
            "claim_type": "research_key_point",
            "topic": topic,
        })
        queue["relations"]["makes_claim"].append({
            "from_id": research_source_id,
            "to_id": claim_id,
        })

    logger.info(
        "Mapped finance-research data",
        topic=topic,
        source_count=len(queue["sources"]),
        claim_count=len(queue["claims"]),
    )
    return queue


# ---------------------------------------------------------------------------
# Command → mapper registry
# ---------------------------------------------------------------------------

COMMAND_MAPPERS: dict[str, MapperFn] = {
    "finance-news-workflow": map_finance_news,
    "ai-research-collect": map_ai_research,
    "generate-market-report": map_market_report,
    "dr-stock": map_dr_stock,
    "ca-eval": map_ca_eval,
    "dr-industry": map_dr_industry,
    "finance-research": map_finance_research,
}


# ---------------------------------------------------------------------------
# Output and cleanup
# ---------------------------------------------------------------------------


def cleanup_old_files(
    base_dir: Path,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> int:
    """Remove graph-queue files older than *max_age_days*.

    Parameters
    ----------
    base_dir : Path
        Base directory containing command sub-directories with queue files.
    max_age_days : int, optional
        Maximum age in days (default 7).

    Returns
    -------
    int
        Number of files removed.
    """
    if not base_dir.exists():
        logger.info("Cleanup: base directory does not exist", path=str(base_dir))
        return 0

    cutoff = time.time() - (max_age_days * 86400)
    removed = 0

    for json_file in base_dir.rglob("gq-*.json"):
        try:
            if json_file.stat().st_mtime < cutoff:
                json_file.unlink()
                removed += 1
                logger.debug("Removed old queue file", path=str(json_file))
        except OSError as exc:
            logger.warning(
                "Failed to remove old queue file",
                path=str(json_file),
                error=str(exc),
            )

    logger.info(
        "Cleanup completed",
        base_dir=str(base_dir),
        max_age_days=max_age_days,
        removed_count=removed,
    )
    return removed


def write_output(queue: dict[str, Any], output_dir: Path) -> Path:
    """Write a graph-queue dict to a JSON file.

    Parameters
    ----------
    queue : dict[str, Any]
        Complete graph-queue dict to serialise.
    output_dir : Path
        Directory to write the output file into.

    Returns
    -------
    Path
        Path to the written JSON file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    queue_id = queue.get("queue_id", generate_queue_id())
    output_path = output_dir / f"{queue_id}.json"

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    logger.info("Wrote graph-queue file", path=str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI.

    Returns
    -------
    argparse.ArgumentParser
        Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Emit graph-queue JSON from various command outputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert dr-stock analysis
  uv run python scripts/emit_graph_queue.py --command dr-stock \\
      --input research/DR_stock_20260213_MCO/03_analysis/stock-analysis.json

  # Convert ca-eval claims
  uv run python scripts/emit_graph_queue.py --command ca-eval \\
      --input analyst/research/CA_eval_20260220-0931_MCO/02_claims/claims.json

  # Cleanup old queue files
  uv run python scripts/emit_graph_queue.py --cleanup

  # Custom cleanup age
  uv run python scripts/emit_graph_queue.py --cleanup --max-age-days 14

Supported commands:
  finance-news-workflow, ai-research-collect, generate-market-report,
  dr-stock, ca-eval, dr-industry, finance-research
        """,
    )
    parser.add_argument(
        "--command",
        choices=list(COMMAND_MAPPERS.keys()),
        help="Source command whose output to convert.",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Path to the input JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Output directory for the queue file. "
            "Defaults to .tmp/graph-queue/{command}/"
        ),
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help=f"Remove queue files older than --max-age-days (default {DEFAULT_MAX_AGE_DAYS}).",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=DEFAULT_MAX_AGE_DAYS,
        help=f"Maximum age in days for cleanup (default {DEFAULT_MAX_AGE_DAYS}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.

    Parameters
    ----------
    argv : list[str] | None, optional
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 for success, 1 for error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Handle cleanup mode
    if args.cleanup:
        removed = cleanup_old_files(DEFAULT_OUTPUT_BASE, args.max_age_days)
        logger.info("Cleanup finished", removed=removed)
        return 0

    # Validate required args for conversion mode
    if not args.command:
        parser.error("--command is required when not using --cleanup")
    if not args.input:
        parser.error("--input is required when not using --cleanup")

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found", path=str(input_path))
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Read and parse input
    try:
        with input_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse input JSON", path=str(input_path), error=str(exc))
        print(f"Error: Invalid JSON in {input_path}: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        logger.error("Failed to read input file", path=str(input_path), error=str(exc))
        print(f"Error: Cannot read {input_path}: {exc}", file=sys.stderr)
        return 1

    # Wrap raw arrays in a dict (e.g. finance-news batch is a bare array)
    if isinstance(raw_data, list):
        raw_data = {"articles": raw_data}

    # Inject input path metadata for traceability
    raw_data["_input_path"] = str(input_path)

    # Run the mapper
    mapper = COMMAND_MAPPERS[args.command]
    try:
        queue = mapper(raw_data)
    except Exception as exc:
        logger.error(
            "Mapper failed",
            command=args.command,
            error=str(exc),
            exc_info=True,
        )
        print(
            f"Error: Mapper '{args.command}' failed: {exc}",
            file=sys.stderr,
        )
        return 1

    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = DEFAULT_OUTPUT_BASE / args.command

    # Write output
    output_path = write_output(queue, output_dir)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
