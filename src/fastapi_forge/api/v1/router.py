"""Aggregate API v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from fastapi_forge.api.v1.endpoints import items

api_router = APIRouter()
api_router.include_router(items.router, prefix="/items", tags=["items"])
