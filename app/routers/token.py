"""GitHub installation token proxy endpoint."""

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db, get_redis
from app.models.installation_registry import InstallationRegistry
from app.services.license_service import validate_license
from app.services.token_service import check_rate_limit, get_cached_token
from app.utils.security import hash_key

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/github", tags=["token-proxy"])


@router.get("/token")
async def get_installation_token(
    installation_id: int = Query(..., description="GitHub App installation ID"),
    authorization: str = Header(..., description="Bearer {license_key}"),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """Return a GitHub installation access token for a given installation ID.

    Auth: Bearer {license_key}

    The GitHub App private key never leaves this service. Callers receive only a
    short-lived installation token (valid 60 min, cached 55 min).

    Rate limited: token_rate_limit_per_minute requests/min per license key.
    """
    settings = get_settings()

    # Parse Bearer token
    scheme, _, key = authorization.partition(" ")
    if scheme.lower() != "bearer" or not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Validate license
    try:
        license_ = await validate_license(db, key)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Rate limit per license key
    key_hash = hash_key(key)
    allowed = await check_rate_limit(key_hash, redis, settings.token_rate_limit_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Slow down token requests.",
            headers={"Retry-After": "60"},
        )

    # Verify this installation belongs to the requesting license
    result = await db.execute(
        select(InstallationRegistry).where(
            InstallationRegistry.installation_id == installation_id,
            InstallationRegistry.license_id == license_.id,
        )
    )
    registry = result.scalar_one_or_none()
    if registry is None:
        log.warning(
            "token_denied_unknown_installation",
            installation_id=installation_id,
            license_id=str(license_.id),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Installation {installation_id} is not registered under this license. "
                "Call POST /installations/register first."
            ),
        )

    # Mint / return cached token
    token_data = await get_cached_token(installation_id, redis)
    log.info("token_issued", installation_id=installation_id, license_id=str(license_.id))
    return token_data
