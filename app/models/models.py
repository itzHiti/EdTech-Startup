import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False, default="")
    # Either Google OAuth (`google_id`) or email/password (`password_hash`) or both may be set.
    google_id = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    total_xp = Column(Integer, nullable=False, default=0)
    lessons_completed = Column(Integer, nullable=False, default=0)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    quiz_results = relationship("QuizResult", back_populates="user", lazy="selectin")
    prompts = relationship("Prompt", back_populates="user", lazy="selectin")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lessons = relationship("Lesson", back_populates="course", lazy="selectin", order_by="Lesson.order_index")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False, default="")
    youtube_url = Column(String(512), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    course = relationship("Course", back_populates="lessons")
    quiz = relationship("Quiz", back_populates="lesson", uselist=False, lazy="selectin")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False)
    questions = Column(JSON, nullable=False)  # list of {question, options[], correct_index}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lesson = relationship("Lesson", back_populates="quiz")


class QuizResult(Base):
    __tablename__ = "quiz_results"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_result"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSON, nullable=False)  # list of chosen indices
    score = Column(Integer, nullable=False, default=0)  # number of correct answers
    xp_gained = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="quiz_results")


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,      # we filter by user_id often
    )
    name = Column(String(100), nullable=False, default="Untitled")
    prompt_type = Column(
        String(20),
        nullable=False,
        default="image",
        index=True,      # we filter by type in list endpoint
    )
    blocks = Column(JSON, nullable=False)
    final_prompt = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    user = relationship("User", back_populates="prompts")
