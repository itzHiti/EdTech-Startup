from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    id_token: str


class EmailPasswordSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str


class EmailPasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    total_xp: int
    lessons_completed: int
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None


# ── Course ────────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    name: str
    description: str = ""
    order_index: int = 0


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None


class CourseOut(BaseModel):
    id: int
    name: str
    description: str
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Lesson ────────────────────────────────────────────────────────────────────

class LessonCreate(BaseModel):
    course_id: int
    title: str
    content: str = ""
    youtube_url: Optional[str] = None
    order_index: int = 0


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    youtube_url: Optional[str] = None
    order_index: Optional[int] = None


class LessonOut(BaseModel):
    id: int
    course_id: int
    title: str
    content: str
    youtube_url: Optional[str]
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Quiz ──────────────────────────────────────────────────────────────────────

class QuestionOut(BaseModel):
    question: str
    options: list[str]


class QuizOut(BaseModel):
    id: int
    lesson_id: int
    questions: list[QuestionOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class QuizSubmit(BaseModel):
    answers: list[int]  # indices of chosen options, one per question


class QuizResultOut(BaseModel):
    id: int
    user_id: int
    lesson_id: int
    answers: list[int]
    score: int
    xp_gained: int
    completed_at: datetime
    questions: list[dict] | None = None  # populated from quiz when returning results

    model_config = {"from_attributes": True}


# ── Prompt ────────────────────────────────────────────────────────────────────

class PromptBlockIn(BaseModel):
    type: str  # subject, location, style, camera, action, or custom
    value: str


class PromptCreate(BaseModel):
    blocks: list[PromptBlockIn]


class PromptOut(BaseModel):
    id: int
    user_id: int
    name: str
    blocks: list[dict]
    final_prompt: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: str
    total_xp: int
    lessons_completed: int
    created_at: datetime

    model_config = {"from_attributes": True}
