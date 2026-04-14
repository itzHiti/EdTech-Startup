from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database.database import engine, Base
from app.models.models import User, Course, Lesson, Quiz, QuizResult, Prompt  # noqa: F401 – ensure models registered

from app.routers.auth import router as auth_router
from app.routers.profile import router as profile_router
from app.routers.courses import router as courses_router
from app.routers.quizzes import router as quizzes_router
from app.routers.prompts import router as prompts_router
from app.routers.image_generation import router as image_generation_router
from app.routers.audio_generation import router as audio_generation_router
from app.internal.admin import router as admin_router
import multiprocessing

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and apply lightweight, idempotent migrations on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure new auth-related columns exist for legacy databases
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")
        )
        await conn.execute(
            text("ALTER TABLE users ALTER COLUMN google_id DROP NOT NULL")
        )
        await conn.execute(
            text("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS image_urls JSON DEFAULT '[]'::json")
        )
        await conn.execute(
            text("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS task_text TEXT DEFAULT ''")
        )
        await conn.execute(
            text("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS section_name VARCHAR(255) DEFAULT 'General'")
        )
        await conn.execute(
            text("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS blocks JSON DEFAULT '[]'::json")
        )
        await conn.execute(
            text("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS mini_quiz JSON DEFAULT '[]'::json")
        )
    yield
    await engine.dispose()


app = FastAPI(
    title="EdTech Platform API",
    description="Skill-building educational platform with AI-powered quiz generation and prompt builder",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS – allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(courses_router)
app.include_router(quizzes_router)
app.include_router(prompts_router)
app.include_router(image_generation_router)
app.include_router(audio_generation_router)
app.include_router(admin_router)


@app.get("/", tags=["/health"])
async def root():
    print("Number of cpu : ", multiprocessing.cpu_count())
    return {"message": "the server is running", "docs": "/docs"}