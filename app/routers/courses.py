from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database.database import get_db
from app.models.models import Course, Lesson, User
from app.schemas import CourseOut, LessonOut

router = APIRouter(tags=["Courses & Lessons"])


@router.get("/courses", response_model=list[CourseOut])
async def list_courses(db: AsyncSession = Depends(get_db)):
    """List all courses ordered by order_index."""
    result = await db.execute(select(Course).order_by(Course.order_index))
    return result.scalars().all()


@router.get("/courses/{course_id}/lessons", response_model=list[LessonOut])
async def list_lessons(course_id: int, db: AsyncSession = Depends(get_db)):
    """List lessons in a course ordered by order_index."""
    # Check course exists
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    result = await db.execute(
        select(Lesson).where(Lesson.course_id == course_id).order_by(Lesson.order_index)
    )
    return result.scalars().all()


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(lesson_id: int, db: AsyncSession = Depends(get_db)):
    """Get lesson details – students can access any lesson."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson
