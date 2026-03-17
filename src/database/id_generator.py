"""Deterministic ID generation for knowledge graph entities.

Provides UUID5/SHA-256 based ID generation functions for sources,
entities, claims, facts, topics, authors, datapoints, fiscal periods,
and insights. All functions are deterministic: the same inputs always
produce the same output.

Functions
---------
generate_source_id
    Generate a UUID5-based ID from a source URL.
generate_entity_id
    Generate a UUID5-based ID from an entity name and type.
generate_claim_id
    Generate a SHA-256 based short ID from claim content.
generate_fact_id
    Generate a SHA-256 based short ID from fact content.
generate_topic_id
    Generate a UUID5-based ID from a topic name and category.
generate_author_id
    Generate a UUID5-based ID from an author name and type.
generate_datapoint_id
    Generate a SHA-256 based short ID from datapoint content.
generate_datapoint_id_from_fields
    Generate a SHA-256 based short ID from source hash, metric, and period.
generate_fiscal_period_id
    Generate a deterministic period ID from ticker and period label.
generate_insight_id
    Generate a date-based sequential insight ID.

Examples
--------
>>> generate_source_id("https://example.com/report.pdf")  # doctest: +ELLIPSIS
'...'
>>> id1 = generate_source_id("https://example.com/report.pdf")
>>> id2 = generate_source_id("https://example.com/report.pdf")
>>> id1 == id2
True
"""

from __future__ import annotations

import hashlib
import uuid

from utils_core.logging import get_logger

logger = get_logger(__name__)


def _sha256_prefix(key: str, length: int = 32) -> str:
    """Return the first *length* hex characters of a SHA-256 hash.

    Parameters
    ----------
    key : str
        Input text to hash.
    length : int, optional
        Number of hex characters to return (default 32, i.e. 128-bit).

    Returns
    -------
    str
        First *length* hex characters of the SHA-256 digest.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:length]


def generate_source_id(url: str) -> str:
    """Generate a deterministic source ID from a URL.

    Uses UUID5 with NAMESPACE_URL to produce the same ID for the same URL.

    Parameters
    ----------
    url : str
        The source URL (e.g., a web page URL or report URL).

    Returns
    -------
    str
        UUID5 string derived from the URL.

    Examples
    --------
    >>> id1 = generate_source_id("https://example.com/q4.pdf")
    >>> id2 = generate_source_id("https://example.com/q4.pdf")
    >>> id1 == id2
    True
    >>> len(id1)
    36
    """
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


def generate_entity_id(name: str, entity_type: str) -> str:
    """Generate a deterministic entity ID from name and type.

    Uses UUID5 with NAMESPACE_URL to produce the same ID for the same
    ``(name, entity_type)`` pair.

    Parameters
    ----------
    name : str
        Entity name (e.g., "Apple", "S&P 500").
    entity_type : str
        Entity type (e.g., "company", "index").

    Returns
    -------
    str
        UUID5 string derived from ``entity:{name}:{entity_type}``.

    Examples
    --------
    >>> id1 = generate_entity_id("Apple", "company")
    >>> id2 = generate_entity_id("Apple", "company")
    >>> id1 == id2
    True
    >>> generate_entity_id("Apple", "company") != generate_entity_id("Google", "company")
    True
    """
    key = f"entity:{name}:{entity_type}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def generate_claim_id(content: str) -> str:
    """Generate a deterministic claim ID from content.

    Parameters
    ----------
    content : str
        Claim content text.

    Returns
    -------
    str
        First 32 hex characters (128-bit) of the SHA-256 hash of *content*.

    Examples
    --------
    >>> id1 = generate_claim_id("S&P 500 rose 2% this week.")
    >>> id2 = generate_claim_id("S&P 500 rose 2% this week.")
    >>> id1 == id2
    True
    >>> len(id1)
    32
    """
    return _sha256_prefix(content)


def generate_fact_id(content: str) -> str:
    """Generate a deterministic fact ID from content.

    Uses a ``fact:`` prefix before hashing to ensure fact IDs never
    collide with claim IDs even when the content text is identical.

    Parameters
    ----------
    content : str
        Fact content text.

    Returns
    -------
    str
        First 32 hex characters (128-bit) of the SHA-256 hash of ``fact:{content}``.

    Examples
    --------
    >>> id1 = generate_fact_id("Revenue was $100B in Q4")
    >>> id2 = generate_fact_id("Revenue was $100B in Q4")
    >>> id1 == id2
    True
    >>> len(id1)
    32
    """
    return _sha256_prefix(f"fact:{content}")


def generate_topic_id(name: str, category: str) -> str:
    """Generate a deterministic topic ID from name and category.

    Uses UUID5 with NAMESPACE_URL to produce the same ID for the same
    ``(name, category)`` pair.

    Parameters
    ----------
    name : str
        Topic name (e.g., "AI Semiconductors", "Fed Rate Decision").
    category : str
        Topic category (e.g., "ai", "macro", "sector").

    Returns
    -------
    str
        UUID5 string derived from ``topic:{name}:{category}``.

    Examples
    --------
    >>> id1 = generate_topic_id("AI Semiconductors", "ai")
    >>> id2 = generate_topic_id("AI Semiconductors", "ai")
    >>> id1 == id2
    True
    >>> generate_topic_id("AI", "ai") != generate_topic_id("Fed", "macro")
    True
    """
    key = f"topic:{name}:{category}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def generate_author_id(name: str, author_type: str) -> str:
    """Generate a deterministic author ID from name and type.

    Uses UUID5 with NAMESPACE_URL to produce the same ID for the same
    ``(name, author_type)`` pair.

    Parameters
    ----------
    name : str
        Author name (e.g., "Goldman Sachs", "John Smith").
    author_type : str
        Author type (e.g., "sell_side", "person", "media").

    Returns
    -------
    str
        UUID5 string derived from ``author:{name}:{author_type}``.

    Examples
    --------
    >>> id1 = generate_author_id("Goldman Sachs", "sell_side")
    >>> id2 = generate_author_id("Goldman Sachs", "sell_side")
    >>> id1 == id2
    True
    >>> generate_author_id("GS", "sell_side") != generate_author_id("MS", "sell_side")
    True
    >>> len(generate_author_id("GS", "sell_side"))
    36
    """
    key = f"author:{name}:{author_type}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def generate_datapoint_id(content: str) -> str:
    """Generate a deterministic datapoint ID from content text.

    Uses the first 32 hex characters (128-bit) of the SHA-256 hash of
    *content*.

    Parameters
    ----------
    content : str
        The datapoint content text.

    Returns
    -------
    str
        First 32 hex characters (128-bit) of the SHA-256 hash of *content*.

    Examples
    --------
    >>> id1 = generate_datapoint_id("GDP grew 2.5% in Q4")
    >>> id2 = generate_datapoint_id("GDP grew 2.5% in Q4")
    >>> id1 == id2
    True
    >>> len(id1)
    32
    """
    return _sha256_prefix(content)


def generate_datapoint_id_from_fields(
    source_hash: str, metric: str, period: str
) -> str:
    """Generate a deterministic datapoint ID from source hash, metric, and period.

    Uses SHA-256 hashing with colon-delimited fields to prevent ID collisions
    caused by special characters (e.g., underscores) in LLM-generated text.

    Parameters
    ----------
    source_hash : str
        The SHA-256 hash of the source document.
    metric : str
        Metric name (e.g., 'Revenue', 'EBITDA').
    period : str
        Period label (e.g., 'FY2025', '4Q25').

    Returns
    -------
    str
        First 32 hex characters (128-bit) of the SHA-256 hash.

    Examples
    --------
    >>> id1 = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
    >>> id2 = generate_datapoint_id_from_fields("abc", "Revenue", "FY2025")
    >>> id1 == id2
    True
    >>> len(id1)
    32
    """
    key = f"{source_hash}:{metric}:{period}"
    return _sha256_prefix(key)


def generate_fiscal_period_id(ticker: str, period_label: str) -> str:
    """Generate a deterministic fiscal period ID from ticker and period label.

    Format: ``{ticker}_{period_label}`` (e.g., ``AAPL_FY2025``).

    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g., "AAPL", "MSFT").
    period_label : str
        Period label (e.g., "FY2025", "4Q25", "1H26").

    Returns
    -------
    str
        Concatenated ``{ticker}_{period_label}``.

    Examples
    --------
    >>> generate_fiscal_period_id("AAPL", "FY2025")
    'AAPL_FY2025'
    >>> generate_fiscal_period_id("MSFT", "4Q25")
    'MSFT_4Q25'
    """
    return f"{ticker}_{period_label}"


def generate_insight_id(date_str: str, sequence: int) -> str:
    """Generate a date-based sequential insight ID.

    Format: ``ins-{date_str}-{sequence:04d}`` (e.g., ``ins-2026-03-17-0001``).

    Parameters
    ----------
    date_str : str
        Date string in YYYY-MM-DD format.
    sequence : int
        Sequential number within the date.

    Returns
    -------
    str
        Formatted insight ID.

    Examples
    --------
    >>> generate_insight_id("2026-03-17", 1)
    'ins-2026-03-17-0001'
    >>> generate_insight_id("2026-03-17", 42)
    'ins-2026-03-17-0042'
    """
    return f"ins-{date_str}-{sequence:04d}"
