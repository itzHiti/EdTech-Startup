"""Tests for user profile endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    """GET /profile without auth should return 403."""
    resp = await client.get("/profile")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers: dict, test_user):
    """GET /profile with valid auth should return the user profile."""
    resp = await client.get("/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "testuser@example.com"
    assert data["full_name"] == "Test User"
    assert data["total_xp"] == 0
    assert data["lessons_completed"] == 0


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers: dict, test_user):
    """PUT /profile should update the user's full_name."""
    resp = await client.put(
        "/profile",
        headers=auth_headers,
        json={"full_name": "Updated Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Name"
