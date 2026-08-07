"""
Cache-aside pattern for read-heavy, rarely-changing data (movie listings,
show details). Reads check Redis first; on a miss, the caller queries
Postgres and populates the cache. Writes explicitly invalidate the relevant
keys rather than trying to keep the cache in sync automatically — explicit
invalidation is simpler to reason about and less error-prone than trying to
update a cached blob in place.
"""

import json
from typing import Optional, Any

from app.config import settings
from app.utils.redis_client import redis_client

MOVIE_LIST_PREFIX = "cache:movies:list:"
SHOW_DETAIL_PREFIX = "cache:shows:detail:"


def get_cached(key: str) -> Optional[Any]:
    raw = redis_client.get(key)
    return json.loads(raw) if raw else None


def set_cached(key: str, value: Any, ttl_seconds: int) -> None:
    redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))


def invalidate_movie_list_cache() -> None:
    # Movie listings are filtered/paginated many different ways, so rather
    # than tracking every possible key combination, we invalidate all
    # movie-list cache entries whenever any movie is created, updated, or
    # deleted. Simpler and safe, at the cost of a few extra cache misses.
    keys = redis_client.keys(f"{MOVIE_LIST_PREFIX}*")
    if keys:
        redis_client.delete(*keys)


def invalidate_show_cache(show_id: int) -> None:
    redis_client.delete(f"{SHOW_DETAIL_PREFIX}{show_id}")
