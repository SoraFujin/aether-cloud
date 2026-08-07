"""Pydantic schemas for installation registration."""

import uuid

from pydantic import AnyHttpUrl, BaseModel


class RegisterRequest(BaseModel):
    installation_id: int
    relay_url: AnyHttpUrl


class RegisterResponse(BaseModel):
    id: uuid.UUID
    installation_id: int
    relay_url: str
    # Operator sets this as AETHER_RELAY_SECRET on their self-hosted instance
    relay_secret: str
