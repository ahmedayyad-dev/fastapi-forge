"""Data-access layer for items.

The repository is intentionally storage-agnostic. It is described by a
:class:`ItemRepository` protocol and ships with an in-memory implementation so
the template runs with zero external services. Swap in a SQL/NoSQL
implementation later without touching the service or API layers.
"""

from __future__ import annotations

import asyncio
from typing import Protocol
from uuid import UUID

from fastapi_forge.schemas.items import Item


class ItemRepository(Protocol):
    """Abstract persistence contract for :class:`Item` entities."""

    async def add(self, item: Item) -> Item: ...

    async def get(self, item_id: UUID) -> Item | None: ...

    async def list(self, *, offset: int, limit: int) -> tuple[list[Item], int]: ...

    async def update(self, item_id: UUID, changes: dict[str, object]) -> Item | None: ...

    async def delete(self, item_id: UUID) -> bool: ...


class InMemoryItemRepository:
    """Thread-safe (asyncio) in-memory repository, ideal for demos and tests."""

    def __init__(self) -> None:
        self._items: dict[UUID, Item] = {}
        self._lock = asyncio.Lock()

    async def add(self, item: Item) -> Item:
        async with self._lock:
            self._items[item.id] = item
        return item

    async def get(self, item_id: UUID) -> Item | None:
        async with self._lock:
            return self._items.get(item_id)

    async def list(self, *, offset: int, limit: int) -> tuple[list[Item], int]:
        async with self._lock:
            ordered = sorted(self._items.values(), key=lambda item: item.created_at)
            return ordered[offset : offset + limit], len(ordered)

    async def update(self, item_id: UUID, changes: dict[str, object]) -> Item | None:
        async with self._lock:
            current = self._items.get(item_id)
            if current is None:
                return None
            updated = current.model_copy(update=changes)
            self._items[item_id] = updated
            return updated

    async def delete(self, item_id: UUID) -> bool:
        async with self._lock:
            return self._items.pop(item_id, None) is not None
