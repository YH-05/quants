"""Pydantic V2 response models for the Polymarket API module.

This module provides Pydantic models for validating and serializing
Polymarket API responses. All models use ``extra='ignore'`` to ensure
forward compatibility when the API adds new fields.

Models
------
- OrderBookLevel: Single price level in an order book.
- PricePoint: Single historical price data point.
- OrderBook: Full order book snapshot for a market.
- TradeRecord: A single trade execution.
- PolymarketMarket: A prediction market with tokens.
- PolymarketEvent: A top-level event containing one or more markets.

See Also
--------
market.schema : Similar Pydantic V2 model pattern used for stock/economic data.
market.polymarket.types : Configuration dataclasses for the Polymarket module.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from utils_core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Low-level models
# =============================================================================


class OrderBookLevel(BaseModel):
    """A single price level in an order book.

    Parameters
    ----------
    price : float
        Price at this level (0.0 to 1.0 for prediction markets).
    size : float
        Total size available at this price level.

    Examples
    --------
    >>> level = OrderBookLevel(price=0.55, size=1000.0)
    >>> level.price
    0.55
    """

    model_config = ConfigDict(extra="ignore")

    price: float = Field(..., description="Price at this level")
    size: float = Field(..., description="Total size at this level")


class PricePoint(BaseModel):
    """A single historical price data point.

    The field names ``t`` and ``p`` match the Polymarket CLOB
    ``/prices-history`` endpoint response format.

    Parameters
    ----------
    t : int
        Unix timestamp (seconds since epoch).
    p : float
        Price at the given timestamp.

    Examples
    --------
    >>> point = PricePoint(t=1700000000, p=0.65)
    >>> point.t
    1700000000
    """

    model_config = ConfigDict(extra="ignore")

    t: int = Field(
        ..., description="Unix timestamp (seconds)"
    )  # Unix timestamp (seconds since epoch)
    p: float = Field(
        ..., description="Price at the timestamp"
    )  # Price value (0.0 to 1.0 for prediction markets)


# =============================================================================
# Order Book
# =============================================================================


class OrderBook(BaseModel):
    """Full order book snapshot for a market.

    Parameters
    ----------
    market : str
        The market condition ID.
    asset_id : str
        The asset/token ID within the market.
    bids : list[OrderBookLevel]
        List of bid levels (buy orders), ordered by price descending.
    asks : list[OrderBookLevel]
        List of ask levels (sell orders), ordered by price ascending.
    timestamp : datetime | None
        Timestamp when the order book was captured.

    Examples
    --------
    >>> book = OrderBook(
    ...     market="0xabc123",
    ...     asset_id="asset123",
    ...     bids=[OrderBookLevel(price=0.50, size=100.0)],
    ...     asks=[OrderBookLevel(price=0.55, size=200.0)],
    ... )
    >>> len(book.bids)
    1
    """

    model_config = ConfigDict(extra="ignore")

    market: str = Field(..., description="Market condition ID")
    asset_id: str = Field(..., description="Asset/token ID")
    bids: list[OrderBookLevel] = Field(..., description="Bid levels (buy orders)")
    asks: list[OrderBookLevel] = Field(..., description="Ask levels (sell orders)")
    timestamp: datetime | None = Field(default=None, description="Snapshot timestamp")


# =============================================================================
# Trade Record
# =============================================================================


class TradeRecord(BaseModel):
    """A single trade execution record.

    Supports both the legacy API schema (``id``, ``market``, ``asset_id``)
    and the current Data API schema (``conditionId`` aliased to ``market``,
    ``asset`` aliased to ``asset_id``, no ``id`` field). When ``id`` is
    absent a deterministic synthetic ID is generated from the trade's
    ``asset_id``, ``price``, ``size``, and ``timestamp``.

    Parameters
    ----------
    id : str | None
        Unique trade identifier. ``None`` when the API does not provide one;
        a synthetic ID is generated automatically via ``model_validator``.
    market : str | None
        The market condition ID. Accepts both ``market`` (legacy) and
        ``conditionId`` (current API) via alias.
    asset_id : str
        The asset/token ID. Accepts both ``asset_id`` (legacy) and
        ``asset`` (current API) via alias.
    price : float
        Trade execution price.
    size : float
        Trade size (number of shares/contracts).
    side : str | None
        Trade side (e.g., "BUY", "SELL").
    timestamp : datetime | None
        Trade execution timestamp. Accepts both ISO 8601 strings and
        Unix timestamp integers (seconds since epoch).

    Examples
    --------
    >>> trade = TradeRecord(
    ...     id="trade-001",
    ...     market="0xabc123",
    ...     asset_id="asset123",
    ...     price=0.65,
    ...     size=500.0,
    ...     side="BUY",
    ... )
    >>> trade.price
    0.65

    New API format (no ``id``, ``asset`` instead of ``asset_id``):

    >>> trade = TradeRecord.model_validate({
    ...     "asset": "token123",
    ...     "conditionId": "0xabc",
    ...     "price": 0.5,
    ...     "size": 10,
    ...     "side": "BUY",
    ...     "timestamp": 1700000000,
    ... })
    >>> trade.asset_id
    'token123'
    >>> trade.id is not None
    True
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str | None = Field(default=None, description="Unique trade identifier")
    market: str | None = Field(
        default=None,
        alias="conditionId",
        description="Market condition ID",
    )
    asset_id: str = Field(..., alias="asset", description="Asset/token ID")
    price: float = Field(..., description="Trade execution price")
    size: float = Field(..., description="Trade size")
    side: str | None = Field(default=None, description="Trade side")
    timestamp: datetime | None = Field(
        default=None, description="Trade execution timestamp"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def _coerce_timestamp(cls, v: Any) -> datetime | str | None:
        """Convert Unix timestamp integers to UTC datetime objects.

        The current Data API returns timestamps as integer seconds since
        epoch. This validator converts them to timezone-aware ``datetime``
        objects so that downstream code (storage, serialization) handles
        them uniformly.
        """
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=UTC)
        return v

    @model_validator(mode="before")
    @classmethod
    def _generate_synthetic_id(cls, data: Any) -> Any:
        """Generate a deterministic synthetic ID when the API omits ``id``.

        The synthetic ID is a SHA-256 hex digest (first 16 chars) derived
        from ``asset``/``asset_id``, ``price``, ``size``, ``timestamp``,
        ``side``, and ``conditionId``/``market``. This ensures idempotent
        upserts even without a server-provided trade ID.

        Uses ``mode="before"`` to access the raw input dict and include
        all available fields for maximum uniqueness.
        """
        if not isinstance(data, dict):
            return data
        if data.get("id") is not None:
            return data

        # Collect distinguishing fields from raw data
        asset = data.get("asset") or data.get("asset_id") or ""
        price = data.get("price", "")
        size = data.get("size", "")
        ts = data.get("timestamp", "")
        side = data.get("side") or ""
        market = data.get("conditionId") or data.get("market") or ""
        # Include transactionHash or proxyWallet if available for extra uniqueness
        tx_hash = data.get("transactionHash") or data.get("proxyWallet") or ""

        raw = f"{asset}:{price}:{size}:{ts}:{side}:{market}:{tx_hash}"
        data["id"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return data


# =============================================================================
# Market & Event models
# =============================================================================


class PolymarketMarket(BaseModel):
    """A prediction market on Polymarket.

    Contains the market's condition ID, question, token list,
    and optional metadata. The ``tokens`` field stores raw token
    dictionaries from the API response to allow flexible handling
    of varying token schemas.

    Supports both snake_case (internal) and camelCase (Gamma API)
    field names via Pydantic aliases.

    Parameters
    ----------
    condition_id : str
        Unique condition identifier for the market.
    question : str
        The market question (e.g., "Will X happen by Y date?").
    tokens : list[dict[str, Any]]
        List of token definitions (token_id, outcome, price, etc.).
        Defaults to empty list when API response uses ``clobTokenIds`` instead.
    description : str | None
        Detailed market description.
    end_date_iso : str | None
        Market end date in ISO 8601 format.
    active : bool | None
        Whether the market is currently active.
    closed : bool | None
        Whether the market is closed/resolved.
    volume : float | None
        Total trading volume.
    liquidity : float | None
        Current liquidity in the market.

    Examples
    --------
    >>> market = PolymarketMarket(
    ...     condition_id="0xabc123",
    ...     question="Will X happen?",
    ...     tokens=[{"token_id": "tok1", "outcome": "Yes", "price": 0.65}],
    ... )
    >>> market.question
    'Will X happen?'
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    condition_id: str = Field(
        ..., alias="conditionId", description="Market condition ID"
    )
    question: str = Field(..., description="Market question")
    tokens: list[dict[str, Any]] = Field(
        default_factory=list, description="Token definitions"
    )
    description: str | None = Field(default=None, description="Market description")
    end_date_iso: str | None = Field(
        default=None, alias="endDateIso", description="End date (ISO 8601)"
    )
    active: bool | None = Field(default=None, description="Whether market is active")
    closed: bool | None = Field(default=None, description="Whether market is closed")
    volume: float | None = Field(default=None, description="Total trading volume")
    liquidity: float | None = Field(default=None, description="Current liquidity")

    @field_validator("volume", "liquidity", mode="before")
    @classmethod
    def _coerce_numeric(cls, v: Any) -> float | None:
        """Coerce string numeric values to float.

        The Gamma API sometimes returns volume/liquidity as strings.
        """
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @model_validator(mode="before")
    @classmethod
    def _build_tokens_from_clob_ids(cls, data: Any) -> Any:
        """Build ``tokens`` list from ``clobTokenIds`` when ``tokens`` is absent.

        The Gamma API does not include a ``tokens`` field in market objects
        nested within events. Instead it provides ``clobTokenIds`` (list of
        token ID strings), ``outcomes`` (JSON string like '["Yes","No"]'),
        and ``outcomePrices`` (JSON string like '["0.55","0.45"]').

        This validator synthesises the ``tokens`` list from those fields
        so that downstream code (storage, collector) can operate uniformly.
        """
        if not isinstance(data, dict):
            return data

        # If tokens is already provided and non-empty, skip
        if data.get("tokens"):
            return data

        raw_clob_ids = data.get("clobTokenIds")
        if not raw_clob_ids:
            return data

        # Parse clobTokenIds (JSON string or list)
        if isinstance(raw_clob_ids, str):
            try:
                clob_ids = json.loads(raw_clob_ids)
            except (json.JSONDecodeError, TypeError):
                clob_ids = []
        elif isinstance(raw_clob_ids, list):
            clob_ids = raw_clob_ids
        else:
            clob_ids = []

        if not clob_ids:
            return data

        # Parse outcomes (JSON string or list)
        raw_outcomes = data.get("outcomes")
        if isinstance(raw_outcomes, str):
            try:
                outcomes = json.loads(raw_outcomes)
            except (json.JSONDecodeError, TypeError):
                outcomes = []
        elif isinstance(raw_outcomes, list):
            outcomes = raw_outcomes
        else:
            outcomes = []

        # Parse outcomePrices (JSON string or list)
        raw_prices = data.get("outcomePrices")
        if isinstance(raw_prices, str):
            try:
                outcome_prices = json.loads(raw_prices)
            except (json.JSONDecodeError, TypeError):
                outcome_prices = []
        elif isinstance(raw_prices, list):
            outcome_prices = raw_prices
        else:
            outcome_prices = []

        # Build tokens list
        tokens: list[dict[str, Any]] = []
        for i, token_id in enumerate(clob_ids):
            tok: dict[str, Any] = {"token_id": str(token_id)}
            if i < len(outcomes):
                tok["outcome"] = str(outcomes[i])
            if i < len(outcome_prices):
                try:
                    tok["price"] = float(outcome_prices[i])
                except (ValueError, TypeError):
                    pass
            tokens.append(tok)

        data["tokens"] = tokens
        return data


class PolymarketEvent(BaseModel):
    """A top-level event on Polymarket containing one or more markets.

    Supports both snake_case (internal) and camelCase (Gamma API)
    field names via Pydantic aliases.

    Parameters
    ----------
    id : str
        Unique event identifier.
    title : str
        Event title (e.g., "US Presidential Election 2028").
    slug : str
        URL-friendly event slug.
    markets : list[PolymarketMarket]
        List of markets belonging to this event.
    description : str | None
        Detailed event description.
    start_date : str | None
        Event start date (ISO 8601).
    end_date : str | None
        Event end date (ISO 8601).
    active : bool | None
        Whether the event is currently active.
    closed : bool | None
        Whether the event is closed.
    volume : float | None
        Total trading volume across all markets.
    liquidity : float | None
        Total liquidity across all markets.

    Examples
    --------
    >>> event = PolymarketEvent(
    ...     id="event-001",
    ...     title="US Presidential Election 2028",
    ...     slug="us-presidential-election-2028",
    ...     markets=[],
    ... )
    >>> event.title
    'US Presidential Election 2028'
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(..., description="Event identifier")
    title: str = Field(..., description="Event title")
    slug: str = Field(..., description="URL-friendly slug")
    markets: list[PolymarketMarket] = Field(..., description="Markets in this event")
    description: str | None = Field(default=None, description="Event description")
    start_date: str | None = Field(
        default=None, alias="startDate", description="Start date (ISO 8601)"
    )
    end_date: str | None = Field(
        default=None, alias="endDate", description="End date (ISO 8601)"
    )
    active: bool | None = Field(default=None, description="Whether event is active")
    closed: bool | None = Field(default=None, description="Whether event is closed")
    volume: float | None = Field(default=None, description="Total volume")
    liquidity: float | None = Field(default=None, description="Total liquidity")

    @field_validator("volume", "liquidity", mode="before")
    @classmethod
    def _coerce_numeric(cls, v: Any) -> float | None:
        """Coerce string numeric values to float.

        The Gamma API sometimes returns volume/liquidity as strings.
        """
        if v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


__all__ = [
    "OrderBook",
    "OrderBookLevel",
    "PolymarketEvent",
    "PolymarketMarket",
    "PricePoint",
    "TradeRecord",
]
