"""Tests for course/lesson CRUD (admin) and public listing endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.database.database import async_session


@pytest.mark.asyncio
async def test_list_courses_empty(client: AsyncClient):
    """GET /courses should return 200 with a list (possibly empty)."""
    resp = await client.get("/courses")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_course_requires_admin(client: AsyncClient, auth_headers: dict, test_user):
    """POST /admin/courses with non-admin user should return 403."""
    resp = await client.post(
        "/admin/courses",
        headers=auth_headers,
        json={"name": "Test Course", "description": "Desc", "order_index": 1},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_course_crud(client: AsyncClient, admin_headers: dict, admin_user):
    """Full CRUD cycle for courses via admin endpoints."""
    # CREATE
    resp = await client.post(
        "/admin/courses",
        headers=admin_headers,
        json={"name": "Python 101", "description": "Intro to Python", "order_index": 1},
    )
    assert resp.status_code == 201
    course = resp.json()
    course_id = course["id"]
    assert course["name"] == "Python 101"

    # READ (public)
    resp = await client.get("/courses")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Python 101" in names

    # UPDATE
    resp = await client.put(
        f"/admin/courses/{course_id}",
        headers=admin_headers,
        json={"name": "Python 201"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Python 201"

    # DELETE
    resp = await client.delete(f"/admin/courses/{course_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Course deleted"


@pytest.mark.asyncio
async def test_admin_lesson_crud(client: AsyncClient, admin_headers: dict, admin_user):
    """Full CRUD cycle for lessons via admin endpoints."""
    # Create a course first
    resp = await client.post(
        "/admin/courses",
        headers=admin_headers,
        json={"name": "Temp Course", "description": "For lesson test", "order_index": 99},
    )
    course_id = resp.json()["id"]

    # CREATE lesson
    resp = await client.post(
        "/admin/lessons",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "title": "Variables",
            "content": "Variables store data in Python. You can assign values using = operator.",
            "youtube_url": "https://youtube.com/watch?v=test",
            "order_index": 1,
        },
    )
    assert resp.status_code == 201
    lesson = resp.json()
    lesson_id = lesson["id"]
    assert lesson["title"] == "Variables"

    # READ lessons in course
    resp = await client.get(f"/courses/{course_id}/lessons")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # READ single lesson
    resp = await client.get(f"/lessons/{lesson_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Variables"

    # UPDATE
    resp = await client.put(
        f"/admin/lessons/{lesson_id}",
        headers=admin_headers,
        json={"title": "Variables & Types"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Variables & Types"

    # DELETE lesson, then course
    resp = await client.delete(f"/admin/lessons/{lesson_id}", headers=admin_headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/admin/courses/{course_id}", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_nonexistent_course_lessons(client: AsyncClient):
    """GET /courses/99999/lessons should return 404."""
    resp = await client.get("/courses/99999/lessons")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_lesson(client: AsyncClient):
    """GET /lessons/99999 should return 404."""
    resp = await client.get("/lessons/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_headers: dict, admin_user):
    """GET /admin/users should return a list of users."""
    resp = await client.get("/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(u["email"] == "admin@example.com" for u in resp.json())
