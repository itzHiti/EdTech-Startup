from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database.database import get_db
from app.models.models import Lesson, Quiz, QuizResult, User
from app.core.rate_limiter import gpt_rate_limiter
from app.auth import require_admin
from app.schemas import QuizOut, QuizSubmit, QuizResultOut, QuizUpdate
from app.services.openai_service import generate_quiz

router = APIRouter(tags=["Quizzes"])

XP_PER_CORRECT = 100


@router.get("/admin/lessons/{lesson_id}/quiz", response_model=QuizOut)
async def admin_get_quiz(
    lesson_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found for this lesson")

    safe_questions = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz.questions
    ]

    return QuizOut(
        id=quiz.id,
        lesson_id=quiz.lesson_id,
        questions=safe_questions,
        created_at=quiz.created_at,
    )


@router.put("/admin/lessons/{lesson_id}/quiz", response_model=QuizOut)
async def admin_update_quiz(
    lesson_id: int,
    payload: QuizUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()

    questions = [q.model_dump() for q in payload.questions]

    if quiz is None:
        quiz = Quiz(lesson_id=lesson_id, questions=questions)
        db.add(quiz)
    else:
        quiz.questions = questions

    await db.flush()
    await db.refresh(quiz)

    safe_questions = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz.questions
    ]

    return QuizOut(
        id=quiz.id,
        lesson_id=quiz.lesson_id,
        questions=safe_questions,
        created_at=quiz.created_at,
    )


@router.delete("/admin/lessons/{lesson_id}/quiz")
async def admin_delete_quiz(
    lesson_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found for this lesson")

    await db.delete(quiz)
    return {"message": "Quiz deleted"}


@router.get("/lessons/{lesson_id}/quiz", response_model=QuizOut)
async def get_quiz(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the quiz for a lesson. Generates one via GPT if it doesn't exist yet."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    # Check if quiz already exists
    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()

    if quiz is None:
        if not lesson.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lesson has no content to generate a quiz from",
            )

        # Rate limit check
        gpt_rate_limiter.check(user.id)

        # Generate quiz questions via GPT
        questions = await generate_quiz(lesson.content)
        quiz = Quiz(lesson_id=lesson_id, questions=questions)
        db.add(quiz)
        await db.flush()
        await db.refresh(quiz)

    # Strip correct_index from the response so students don't see the answers
    safe_questions = [
        {"question": q["question"], "options": q["options"]}
        for q in quiz.questions
    ]

    return QuizOut(
        id=quiz.id,
        lesson_id=quiz.lesson_id,
        questions=safe_questions,
        created_at=quiz.created_at,
    )


@router.post("/lessons/{lesson_id}/quiz/submit", response_model=QuizResultOut)
async def submit_quiz(
    lesson_id: int,
    payload: QuizSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit quiz answers. Non-retakeable – returns 409 if already submitted."""
    # Check for existing result
    existing = await db.execute(
        select(QuizResult).where(
            QuizResult.user_id == user.id,
            QuizResult.lesson_id == lesson_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quiz already submitted for this lesson",
        )

    # Fetch quiz
    result = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found for this lesson")

    if len(payload.answers) != len(quiz.questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {len(quiz.questions)} answers, got {len(payload.answers)}",
        )

    # Grade
    score = 0
    for i, q in enumerate(quiz.questions):
        if payload.answers[i] == q["correct_index"]:
            score += 1

    xp_gained = score * XP_PER_CORRECT

    # Save result
    quiz_result = QuizResult(
        user_id=user.id,
        lesson_id=lesson_id,
        answers=payload.answers,
        score=score,
        xp_gained=xp_gained,
    )
    db.add(quiz_result)

    # Update user stats
    user.total_xp += xp_gained
    user.lessons_completed += 1

    await db.flush()
    await db.refresh(quiz_result)

    # Return result with questions included for review
    return QuizResultOut(
        id=quiz_result.id,
        user_id=quiz_result.user_id,
        lesson_id=quiz_result.lesson_id,
        answers=quiz_result.answers,
        score=quiz_result.score,
        xp_gained=quiz_result.xp_gained,
        completed_at=quiz_result.completed_at,
        questions=quiz.questions,
    )


@router.get("/quiz-results/{lesson_id}", response_model=QuizResultOut)
async def get_quiz_result(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's quiz result for a lesson."""
    result = await db.execute(
        select(QuizResult).where(
            QuizResult.user_id == user.id,
            QuizResult.lesson_id == lesson_id,
        )
    )
    quiz_result = result.scalar_one_or_none()
    if quiz_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No result found for this lesson")

    # Also fetch the quiz questions so user can review correct answers
    quiz_res = await db.execute(select(Quiz).where(Quiz.lesson_id == lesson_id))
    quiz = quiz_res.scalar_one_or_none()

    return QuizResultOut(
        id=quiz_result.id,
        user_id=quiz_result.user_id,
        lesson_id=quiz_result.lesson_id,
        answers=quiz_result.answers,
        score=quiz_result.score,
        xp_gained=quiz_result.xp_gained,
        completed_at=quiz_result.completed_at,
        questions=quiz.questions if quiz else None,
    )
