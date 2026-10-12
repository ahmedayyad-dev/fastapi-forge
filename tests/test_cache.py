"""Tests for the JSON cache facade."""

from __future__ import annotations

from fastapi_forge.core.cache import Cache


async def test_set_get_delete(cache: Cache) -> None:
    assert await cache.get("missing") is None
    await cache.set("greeting", {"hello": "world"})
    assert await cache.get("greeting") == {"hello": "world"}
    assert await cache.exists("greeting") is True
    assert await cache.delete("greeting") == 1
    assert await cache.get("greeting") is None


async def test_get_or_set_computes_once(cache: Cache) -> None:
    calls = 0

    async def factory() -> list[int]:
        nonlocal calls
        calls += 1
        return [1, 2, 3]

    assert await cache.get_or_set("numbers", factory) == [1, 2, 3]
    assert await cache.get_or_set("numbers", factory) == [1, 2, 3]
    assert calls == 1
