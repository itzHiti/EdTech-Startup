"""Tests for quiz endpoints (without calling real OpenAI)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.database.database import async_session
from app.models.models import Course, Lesson, Quiz


@pytest.fixture
async def lesson_with_quiz(admin_headers, client):
    """Create a course → lesson → quiz for testing quiz submission."""
    # Create course
    resp = await client.post(
        "/admin/courses",
        headers=admin_headers,
        json={"name": "Quiz Test Course", "description": "For quiz tests", "order_index": 50},
    )
    course_id = resp.json()["id"]

    # Create lesson
    resp = await client.post(
        "/admin/lessons",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "title": "Quiz Lesson",
            "content": "This is lesson content for quiz generation.",
            "order_index": 1,
        },
    )
    lesson_id = resp.json()["id"]

    # Manually insert a quiz (bypass OpenAI)
    questions = [
        {"question": "What is 1+1?", "options": ["1", "2", "3", "4"], "correct_index": 1},
        {"question": "What is 2+2?", "options": ["3", "4", "5", "6"], "correct_index": 1},
        {"question": "What is 3+3?", "options": ["5", "6", "7", "8"], "correct_index": 1},
    ]
    async with async_session() as session:
        quiz = Quiz(lesson_id=lesson_id, questions=questions)
        session.add(quiz)
        await session.commit()

    yield {"course_id": course_id, "lesson_id": lesson_id}

    # Cleanup
    async with async_session() as session:
        await session.execute(text("DELETE FROM quiz_results WHERE lesson_id = :lid"), {"lid": lesson_id})
        await session.execute(text("DELETE FROM quizzes WHERE lesson_id = :lid"), {"lid": lesson_id})
        await session.execute(text("DELETE FROM lessons WHERE id = :lid"), {"lid": lesson_id})
        await session.execute(text("DELETE FROM courses WHERE id = :cid"), {"cid": course_id})
        await session.commit()


@pytest.mark.asyncio
async def test_get_quiz(client: AsyncClient, auth_headers: dict, test_user, admin_user, admin_headers, lesson_with_quiz):
    """GET /lessons/{id}/quiz should return the quiz without correct_index."""
    lid = lesson_with_quiz["lesson_id"]
    resp = await client.get(f"/lessons/{lid}/quiz", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["questions"]) == 3
    # Verify correct_index is NOT exposed
    for q in data["questions"]:
        assert "correct_index" not in q


@pytest.mark.asyncio
async def test_submit_quiz_all_correct(client: AsyncClient, auth_headers: dict, test_user, admin_user, admin_headers, lesson_with_quiz):
    """POST /lessons/{id}/quiz/submit with all correct answers should award 300 XP."""
    lid = lesson_with_quiz["lesson_id"]
    resp = await client.post(
        f"/lessons/{lid}/quiz/submit",
        headers=auth_headers,
        json={"answers": [1, 1, 1]},  # all correct
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 3
    assert data["xp_gained"] == 300
    assert data["questions"] is not None  # includes questions for review


@pytest.mark.asyncio
async def test_submit_quiz_not_retakeable(client: AsyncClient, auth_headers: dict, test_user, admin_user, admin_headers, lesson_with_quiz):
    """Submitting the same quiz twice should return 409."""
    lid = lesson_with_quiz["lesson_id"]
    # First submit
    await client.post(
        f"/lessons/{lid}/quiz/submit",
        headers=auth_headers,
        json={"answers": [0, 0, 0]},
    )
    # Second submit
    resp = await client.post(
        f"/lessons/{lid}/quiz/submit",
        headers=auth_headers,
        json={"answers": [1, 1, 1]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_quiz_result(client: AsyncClient, auth_headers: dict, test_user, admin_user, admin_headers, lesson_with_quiz):
    """GET /quiz-results/{lesson_id} should return the user's result after submission."""
    lid = lesson_with_quiz["lesson_id"]
    # Submit first
    await client.post(
        f"/lessons/{lid}/quiz/submit",
        headers=auth_headers,
        json={"answers": [1, 0, 1]},  # 2 correct
    )
    resp = await client.get(f"/quiz-results/{lid}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 2
    assert data["xp_gained"] == 200


@pytest.mark.asyncio
async def test_get_quiz_nonexistent_lesson(client: AsyncClient, auth_headers: dict, test_user):
    """GET /lessons/99999/quiz should return 404."""
    resp = await client.get("/lessons/99999/quiz", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_quiz_result_not_found(client: AsyncClient, auth_headers: dict, test_user):
    """GET /quiz-results/99999 should return 404 when no result exists."""
    resp = await client.get("/quiz-results/99999", headers=auth_headers)
    assert resp.status_code == 404
