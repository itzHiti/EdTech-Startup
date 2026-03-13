"""Shared fixtures for the EdTech test suite.

Key design:
  • Uses the REAL database (edtech) – tests create their own data and clean up.
  • `auth_headers` creates a temporary test user and returns Bearer headers
    so every authenticated endpoint can be tested without Google OAuth.
  • `admin_headers` does the same but with is_admin=True.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from main import app
from app.database.database import async_session
from app.models.models import User
from app.auth import create_access_token


@pytest.fixture(scope="session")
def event_loop():
    """Provide a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def test_user() -> AsyncGenerator[User, None]:
    """Create a temporary user and clean up after the test."""
    async with async_session() as session:
        user = User(
            email="testuser@example.com",
            full_name="Test User",
            google_id="test_google_id_12345",
            total_xp=0,
            lessons_completed=0,
            is_admin=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user

        # Cleanup – delete everything related to this user
        await session.execute(text("DELETE FROM prompts WHERE user_id = :uid"), {"uid": user.id})
        await session.execute(text("DELETE FROM quiz_results WHERE user_id = :uid"), {"uid": user.id})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})
        await session.commit()


@pytest_asyncio.fixture
async def admin_user() -> AsyncGenerator[User, None]:
    """Create a temporary admin user and clean up after the test."""
    async with async_session() as session:
        user = User(
            email="admin@example.com",
            full_name="Admin User",
            google_id="admin_google_id_12345",
            total_xp=0,
            lessons_completed=0,
            is_admin=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        yield user

        # Cleanup
        await session.execute(text("DELETE FROM prompts WHERE user_id = :uid"), {"uid": user.id})
        await session.execute(text("DELETE FROM quiz_results WHERE user_id = :uid"), {"uid": user.id})
        await session.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user.id})
        await session.commit()


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Return Authorization headers for the test user."""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """Return Authorization headers for the admin user."""
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
