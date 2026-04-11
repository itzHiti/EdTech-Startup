"""Tests for health check and auth endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET / should return the health message."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "EdTech Platform API is running" in data["message"]


@pytest.mark.asyncio
async def test_google_login_invalid_token(client: AsyncClient):
    """POST /auth/google with an invalid token should return 401."""
    resp = await client.post("/auth/google", json={"id_token": "totally-invalid-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """POST /auth/refresh with an invalid token should return 401."""
    resp = await client.post("/auth/refresh", json={"refresh_token": "bad-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """POST /auth/logout should always return 200."""
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_signup_and_login_with_email_password(client: AsyncClient):
    """User can sign up and then log in using email/password."""
    email = f"user-{uuid.uuid4()}@example.com"
    password = "StrongPass123!"

    # Sign up
    signup_resp = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": "New User",
        },
    )
    assert signup_resp.status_code == 201
    signup_data = signup_resp.json()
    assert "access_token" in signup_data
    assert "refresh_token" in signup_data

    # Login with the same credentials
    login_resp = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Login with a wrong password should return 401."""
    email = f"user-{uuid.uuid4()}@example.com"
    password = "StrongPass123!"

    # Create user via signup
    signup_resp = await client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": password,
            "full_name": "Another User",
        },
    )
    assert signup_resp.status_code == 201

    # Attempt login with wrong password
    login_resp = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword!",
        },
    )
    assert login_resp.status_code == 401


@pytest.mark.asyncio
async def test_google_login_requires_existing_google_account(client: AsyncClient, monkeypatch):
    async def fake_verify_google_token(_id_token: str):
        return {
            "aud": "client-id",
            "sub": f"google-{uuid.uuid4()}",
            "email": f"g-{uuid.uuid4()}@example.com",
            "name": "Google User",
        }

    monkeypatch.setattr("app.routers.auth._verify_google_token", fake_verify_google_token)

    login_resp = await client.post("/auth/google", json={"id_token": "valid-token"})
    assert login_resp.status_code == 404
    assert "Please sign up with Google first" in login_resp.json()["detail"]


@pytest.mark.asyncio
async def test_google_signup_then_google_login(client: AsyncClient, monkeypatch):
    google_sub = f"google-{uuid.uuid4()}"

    async def fake_verify_google_token(_id_token: str):
        return {
            "aud": "client-id",
            "sub": google_sub,
            "email": f"g-{uuid.uuid4()}@example.com",
            "name": "Google User",
        }

    monkeypatch.setattr("app.routers.auth._verify_google_token", fake_verify_google_token)

    signup_resp = await client.post("/auth/google/signup", json={"id_token": "valid-token"})
    assert signup_resp.status_code == 201
    assert "access_token" in signup_resp.json()

    login_resp = await client.post("/auth/google", json={"id_token": "valid-token"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
