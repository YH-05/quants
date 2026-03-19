"""academic パッケージのキャッシュアダプタ.

market.cache.SQLiteCache を再利用し、academic パッケージ用に
設定されたキャッシュインスタンスを提供する。

主な機能
--------
- ``get_academic_cache(config)`` : academic 用 SQLiteCache インスタンス取得
- ``make_cache_key(arxiv_id)`` : キャッシュキー生成

キャッシュ設定
--------------
| パラメータ    | デフォルト値 | 説明                 |
|--------------|-------------|----------------------|
| db_path      | data/cache/academic.db | SQLite DB パス |
| TTL          | 604800秒（7日）        | キャッシュ有効期間   |
| max_entries  | 5000                    | 最大エントリ数      |

Examples
--------
>>> from academic.cache import get_academic_cache, make_cache_key
>>> cache = get_academic_cache()
>>> key = make_cache_key("2301.00001")
>>> cache.set(key, paper_data)
>>> cache.get(key)

See Also
--------
market.cache.cache : SQLiteCache コア実装
market.jquants.cache : J-Quants キャッシュアダプタ（参考実装）
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Final

from market.cache.cache import SQLiteCache, create_persistent_cache
from utils_core.logging import get_logger

if TYPE_CHECKING:
    from .types import AcademicConfig

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

ACADEMIC_CACHE_DB_PATH: Final[str] = "data/cache/academic.db"
"""academic キャッシュの SQLite DB パス."""

ACADEMIC_CACHE_TTL: Final[int] = 604800
"""academic キャッシュの TTL（秒）: 7日."""

ACADEMIC_CACHE_MAX_ENTRIES: Final[int] = 5000
"""academic キャッシュの最大エントリ数."""


def get_academic_cache(config: AcademicConfig | None = None) -> SQLiteCache:
    """academic 用の SQLiteCache インスタンスを取得する.

    market.cache.create_persistent_cache() のラッパーとして、
    academic パッケージ用にデフォルト設定された SQLiteCache を返す。
    同一 TTL 設定の場合はシングルトンとしてキャッシュされたインスタンスを返す。

    Parameters
    ----------
    config : AcademicConfig | None
        API 設定。None の場合はデフォルト設定を使用する。
        ``config.cache_ttl`` でカスタム TTL を指定可能。

    Returns
    -------
    SQLiteCache
        academic 用に設定されたキャッシュインスタンス

    Examples
    --------
    >>> cache = get_academic_cache()
    >>> cache.set("academic:paper:2301.00001", data)

    >>> config = AcademicConfig(cache_ttl=3600)
    >>> cache = get_academic_cache(config=config)
    """
    ttl = ACADEMIC_CACHE_TTL
    if config is not None:
        ttl = config.cache_ttl

    return _get_academic_cache_singleton(ttl)


@functools.lru_cache(maxsize=4)
def _get_academic_cache_singleton(ttl: int) -> SQLiteCache:
    """同一 TTL 設定の場合にキャッシュインスタンスをシングルトン化する.

    Parameters
    ----------
    ttl : int
        キャッシュの有効期間（秒）

    Returns
    -------
    SQLiteCache
        academic 用に設定されたキャッシュインスタンス
    """
    cache = create_persistent_cache(
        db_path=ACADEMIC_CACHE_DB_PATH,
        ttl_seconds=ttl,
        max_entries=ACADEMIC_CACHE_MAX_ENTRIES,
    )
    logger.debug(
        "Academic cache instance created",
        db_path=ACADEMIC_CACHE_DB_PATH,
        ttl_seconds=ttl,
        max_entries=ACADEMIC_CACHE_MAX_ENTRIES,
    )
    return cache


def make_cache_key(arxiv_id: str) -> str:
    """arXiv ID からキャッシュキーを生成する.

    Parameters
    ----------
    arxiv_id : str
        arXiv の論文 ID（例: "2301.00001"）

    Returns
    -------
    str
        ``"academic:paper:{arxiv_id}"`` 形式のキャッシュキー

    Examples
    --------
    >>> make_cache_key("2301.00001")
    'academic:paper:2301.00001'

    >>> make_cache_key("2301.00001v2")
    'academic:paper:2301.00001v2'
    """
    return f"academic:paper:{arxiv_id}"


__all__ = [
    "ACADEMIC_CACHE_DB_PATH",
    "ACADEMIC_CACHE_MAX_ENTRIES",
    "ACADEMIC_CACHE_TTL",
    "get_academic_cache",
    "make_cache_key",
]
