"""End-to-end tests for the items CRUD endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def test_full_crud_lifecycle(client: AsyncClient) -> None:
    created = await client.post("/api/v1/items", json={"name": "widget", "price": 9.5})
    assert created.status_code == 201
    item = created.json()
    assert item["name"] == "widget"
    assert item["price"] == 9.5
    item_id = item["id"]

    fetched = await client.get(f"/api/v1/items/{item_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == item_id

    listing = await client.get("/api/v1/items")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert len(listing.json()["items"]) == 1

    updated = await client.patch(f"/api/v1/items/{item_id}", json={"price": 12.0})
    assert updated.status_code == 200
    assert updated.json()["price"] == 12.0

    deleted = await client.delete(f"/api/v1/items/{item_id}")
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/items/{item_id}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


async def test_pagination(client: AsyncClient) -> None:
    for index in range(5):
        await client.post("/api/v1/items", json={"name": f"item-{index}", "price": 1.0})

    page = await client.get("/api/v1/items", params={"limit": 2, "offset": 1})
    payload = page.json()
    assert payload["total"] == 5
    assert payload["limit"] == 2
    assert payload["offset"] == 1
    assert len(payload["items"]) == 2


async def test_validation_error_envelope(client: AsyncClient) -> None:
    response = await client.post("/api/v1/items", json={"name": "", "price": -1})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_update_and_delete_unknown_item(client: AsyncClient) -> None:
    unknown = "00000000-0000-0000-0000-000000000000"
    assert (await client.patch(f"/api/v1/items/{unknown}", json={"price": 1.0})).status_code == 404
    assert (await client.delete(f"/api/v1/items/{unknown}")).status_code == 404
