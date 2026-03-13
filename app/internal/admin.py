from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database.database import get_db
from app.models.models import Course, Lesson, User
from app.schemas import (
    CourseCreate, CourseUpdate, CourseOut,
    LessonCreate, LessonUpdate, LessonOut,
    AdminUserOut,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Course CRUD ───────────────────────────────────────────────────────────────

@router.post("/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    course = Course(**payload.model_dump())
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return course


@router.put("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(course, field, value)

    await db.flush()
    await db.refresh(course)
    return course


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    await db.delete(course)
    return {"message": "Course deleted"}


# ── Lesson CRUD ───────────────────────────────────────────────────────────────

@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Verify course exists
    course = await db.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    lesson = Lesson(**payload.model_dump())
    db.add(lesson)
    await db.flush()
    await db.refresh(lesson)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lesson, field, value)

    await db.flush()
    await db.refresh(lesson)
    return lesson


@router.delete("/lessons/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    await db.delete(lesson)
    return {"message": "Lesson deleted"}


# ── User management ──────────────────────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with their progress."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()
