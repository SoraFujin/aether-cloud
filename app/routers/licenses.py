"""License validation endpoint — called by self-hosted instances at startup."""

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.license import ValidateResponse
from app.services.license_service import validate_license

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.get("/validate", response_model=ValidateResponse)
async def validate_license_key(
    authorization: str = Header(..., description="Bearer {license_key}"),
    db: AsyncSession = Depends(get_db),
):
    """Validate a license key. Called by self-hosted instances during startup.

    Returns 200 with license details if valid.
    Returns 401 for any invalid/expired/revoked key.
    """
    scheme, _, key = authorization.partition(" ")
    if scheme.lower() != "bearer" or not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    try:
        license_ = await validate_license(db, key)
    except ValueError as exc:
        log.warning("license_validation_failed", reason=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired license key",
        )

    return ValidateResponse(
        valid=True,
        customer_email=license_.customer_email,
        expires_at=license_.expires_at,
    )
