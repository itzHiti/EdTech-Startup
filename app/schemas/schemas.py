from datetime import datetime
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


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
    section_name: str = "General"
    image_urls: list[str] = Field(default_factory=list)
    task_text: str = ""
    blocks: list[dict] = Field(default_factory=list)
    mini_quiz: list[dict] = Field(default_factory=list)
    order_index: int = 0


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    youtube_url: Optional[str] = None
    section_name: Optional[str] = None
    image_urls: Optional[list[str]] = None
    task_text: Optional[str] = None
    blocks: Optional[list[dict]] = None
    mini_quiz: Optional[list[dict]] = None
    order_index: Optional[int] = None


class LessonOut(BaseModel):
    id: int
    course_id: int
    title: str
    content: str
    youtube_url: Optional[str]
    section_name: str
    image_urls: list[str]
    task_text: str
    blocks: list[dict]
    mini_quiz: list[dict]
    order_index: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LessonSummaryOut(BaseModel):
    id: int
    course_id: int
    title: str
    section_name: str
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


class QuizQuestionIn(BaseModel):
    question: str
    options: list[str]
    correct_index: int = 0


class QuizUpdate(BaseModel):
    questions: list[QuizQuestionIn]


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

class PromptType(str, Enum):
    image = "image"
    video = "video"
    text = "text"


class PromptBlockIn(BaseModel):
    type: str   # defined freely by frontend: subject, style, tone, etc.
    value: str

    @field_validator("type", "value")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Block type and value must not be empty")
        return v.strip()


class PromptCreate(BaseModel):
    prompt_type: PromptType
    blocks: list[PromptBlockIn]

    @field_validator("blocks")
    @classmethod
    def blocks_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one block is required")
        return v


class PromptUpdate(BaseModel):
    """All fields optional — only provided fields are updated."""
    blocks: list[PromptBlockIn] | None = None
    name: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Name must not be empty")
        return v.strip() if v else v

    @field_validator("blocks")
    @classmethod
    def blocks_not_empty(cls, v: list | None) -> list | None:
        if v is not None and not v:
            raise ValueError("Blocks list must not be empty if provided")
        return v


class PromptOut(BaseModel):
    id: int
    user_id: int
    name: str
    prompt_type: PromptType
    blocks: list[dict]
    final_prompt: str
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ── Image generation ─────────────────────────────────────────────────────────


class GeneratedImageInput(BaseModel):
    data: str
    mime_type: str


class ImageGenerationRequest(BaseModel):
    model: str
    prompt: str
    aspect_ratio: str = "1:1"
    quality: str = "1K"
    images: list[GeneratedImageInput] = Field(default_factory=list)


class GeneratedImageOut(BaseModel):
    data: str
    mime_type: str


class ImageGenerationResponse(BaseModel):
    model: str
    prompt: str
    images: list[GeneratedImageOut]
    text: str | None = None



# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: str
    total_xp: int
    lessons_completed: int
    created_at: datetime

    model_config = {"from_attributes": True}
