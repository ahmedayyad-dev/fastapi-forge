"""CRUD endpoints for the sample ``items`` resource."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from fastapi_forge.api.deps import RateLimit, get_item_service
from fastapi_forge.schemas.items import Item, ItemCreate, ItemPage, ItemUpdate
from fastapi_forge.services.items import ItemService

router = APIRouter(dependencies=[Depends(RateLimit())])

ServiceDep = Annotated[ItemService, Depends(get_item_service)]


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED, summary="Create an item")
async def create_item(payload: ItemCreate, service: ServiceDep) -> Item:
    return await service.create(payload)


@router.get("", response_model=ItemPage, summary="List items")
async def list_items(
    service: ServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ItemPage:
    return await service.list(limit=limit, offset=offset)


@router.get("/{item_id}", response_model=Item, summary="Get an item")
async def get_item(item_id: UUID, service: ServiceDep) -> Item:
    return await service.get(item_id)


@router.patch("/{item_id}", response_model=Item, summary="Update an item")
async def update_item(item_id: UUID, payload: ItemUpdate, service: ServiceDep) -> Item:
    return await service.update(item_id, payload)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
    response_class=Response,
)
async def delete_item(item_id: UUID, service: ServiceDep) -> Response:
    await service.delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
