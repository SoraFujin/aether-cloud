"""Pydantic schemas for license endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.license import LicenseStatus


class LicenseCreateRequest(BaseModel):
    customer_email: EmailStr
    expires_at: datetime | None = None
    notes: str | None = None


class LicenseCreateResponse(BaseModel):
    id: uuid.UUID
    customer_email: str
    status: LicenseStatus
    expires_at: datetime | None
    created_at: datetime
    # Returned ONCE — never stored in plain form
    license_key: str

    model_config = {"from_attributes": True}


class LicenseListItem(BaseModel):
    id: uuid.UUID
    customer_email: str
    status: LicenseStatus
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ValidateResponse(BaseModel):
    valid: bool
    customer_email: str
    expires_at: datetime | None
