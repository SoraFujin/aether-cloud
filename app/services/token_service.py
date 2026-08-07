"""GitHub installation token service with Redis caching and rate limiting."""

from typing import Any

import structlog

from app.github.app import mint_installation_token

log = structlog.get_logger(__name__)

_TOKEN_TTL = 55 * 60          # seconds; GitHub tokens last 60 min
_RATE_LIMIT_WINDOW = 60       # seconds
_RATE_LIMIT_KEY_PREFIX = "rate:token:"


async def get_cached_token(installation_id: int, redis: Any) -> dict[str, str]:
    """Return a cached GitHub installation token, minting fresh if needed.

    Cache key: gh_install_token:{installation_id}
    TTL: 55 minutes
    """
    cache_key = f"gh_install_token:{installation_id}"
    cached = await redis.get(cache_key)
    if cached:
        log.debug("token_cache_hit", installation_id=installation_id)
        # cached value is just the token string; expires_at not needed by callers
        return {"token": cached, "expires_at": ""}

    log.debug("token_cache_miss", installation_id=installation_id)
    result = await mint_installation_token(installation_id)
    await redis.set(cache_key, result["token"], ex=_TOKEN_TTL)
    return result


async def check_rate_limit(license_key_hash: str, redis: Any, limit: int) -> bool:
    """Sliding-window rate limiter. Returns True if request is allowed.

    Uses Redis INCR + EXPIRE: increments a counter per (license_hash, window).
    Allows up to `limit` requests per 60-second window.
    """
    rate_key = f"{_RATE_LIMIT_KEY_PREFIX}{license_key_hash}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, _RATE_LIMIT_WINDOW)
    return count <= limit
