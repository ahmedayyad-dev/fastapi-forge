"""Business logic for items, including cache read-through and invalidation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi_forge.core.cache import Cache
from fastapi_forge.core.exceptions import item_not_found
from fastapi_forge.repos.items import ItemRepository
from fastapi_forge.schemas.items import Item, ItemCreate, ItemPage, ItemUpdate


class ItemService:
    """Coordinates the repository and cache for item operations."""

    def __init__(self, repository: ItemRepository, cache: Cache) -> None:
        self._repository = repository
        self._cache = cache

    @staticmethod
    def _cache_key(item_id: UUID) -> str:
        return f"items:{item_id}"

    async def create(self, payload: ItemCreate) -> Item:
        item = Item(
            id=uuid4(),
            created_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        return await self._repository.add(item)

    async def get(self, item_id: UUID) -> Item:
        key = self._cache_key(item_id)
        cached = await self._cache.get(key)
        if cached is not None:
            return Item.model_validate(cached)

        item = await self._repository.get(item_id)
        if item is None:
            raise item_not_found(item_id)

        await self._cache.set(key, item.model_dump(mode="json"))
        return item

    async def list(self, *, offset: int, limit: int) -> ItemPage:
        items, total = await self._repository.list(offset=offset, limit=limit)
        return ItemPage(items=items, total=total, limit=limit, offset=offset)

    async def update(self, item_id: UUID, payload: ItemUpdate) -> Item:
        changes = payload.model_dump(exclude_unset=True)
        updated = await self._repository.update(item_id, changes)
        if updated is None:
            raise item_not_found(item_id)
        await self._cache.delete(self._cache_key(item_id))
        return updated

    async def delete(self, item_id: UUID) -> None:
        deleted = await self._repository.delete(item_id)
        if not deleted:
            raise item_not_found(item_id)
        await self._cache.delete(self._cache_key(item_id))
