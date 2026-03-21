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

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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

    Parameters
    ----------
    id : str
        Unique trade identifier.
    market : str
        The market condition ID.
    asset_id : str
        The asset/token ID.
    price : float
        Trade execution price.
    size : float
        Trade size (number of shares/contracts).
    side : str | None
        Trade side (e.g., "BUY", "SELL").
    timestamp : datetime | None
        Trade execution timestamp.

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
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique trade identifier")
    market: str = Field(..., description="Market condition ID")
    asset_id: str = Field(..., description="Asset/token ID")
    price: float = Field(..., description="Trade execution price")
    size: float = Field(..., description="Trade size")
    side: str | None = Field(default=None, description="Trade side")
    timestamp: datetime | None = Field(
        default=None, description="Trade execution timestamp"
    )


# =============================================================================
# Market & Event models
# =============================================================================


class PolymarketMarket(BaseModel):
    """A prediction market on Polymarket.

    Contains the market's condition ID, question, token list,
    and optional metadata. The ``tokens`` field stores raw token
    dictionaries from the API response to allow flexible handling
    of varying token schemas.

    Parameters
    ----------
    condition_id : str
        Unique condition identifier for the market.
    question : str
        The market question (e.g., "Will X happen by Y date?").
    tokens : list[dict[str, Any]]
        List of token definitions (token_id, outcome, price, etc.).
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

    model_config = ConfigDict(extra="ignore")

    condition_id: str = Field(..., description="Market condition ID")
    question: str = Field(..., description="Market question")
    tokens: list[dict[str, Any]] = Field(..., description="Token definitions")
    description: str | None = Field(default=None, description="Market description")
    end_date_iso: str | None = Field(default=None, description="End date (ISO 8601)")
    active: bool | None = Field(default=None, description="Whether market is active")
    closed: bool | None = Field(default=None, description="Whether market is closed")
    volume: float | None = Field(default=None, description="Total trading volume")
    liquidity: float | None = Field(default=None, description="Current liquidity")


class PolymarketEvent(BaseModel):
    """A top-level event on Polymarket containing one or more markets.

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

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Event identifier")
    title: str = Field(..., description="Event title")
    slug: str = Field(..., description="URL-friendly slug")
    markets: list[PolymarketMarket] = Field(..., description="Markets in this event")
    description: str | None = Field(default=None, description="Event description")
    start_date: str | None = Field(default=None, description="Start date (ISO 8601)")
    end_date: str | None = Field(default=None, description="End date (ISO 8601)")
    active: bool | None = Field(default=None, description="Whether event is active")
    closed: bool | None = Field(default=None, description="Whether event is closed")
    volume: float | None = Field(default=None, description="Total volume")
    liquidity: float | None = Field(default=None, description="Total liquidity")


__all__ = [
    "OrderBook",
    "OrderBookLevel",
    "PolymarketEvent",
    "PolymarketMarket",
    "PricePoint",
    "TradeRecord",
]
