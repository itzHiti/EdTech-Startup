"""Seed database from markdown files in ./courses.

Usage:
  python seed.py
  python seed.py --reset
"""

import argparse
import asyncio
import re
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.models.models import Base, Course, Lesson, Quiz


ROOT_DIR = Path(__file__).resolve().parent
COURSES_DIR = ROOT_DIR / "courses"
settings = get_settings() if callable(get_settings) else Settings()

COURSE_NAME_BY_FILE = {
    "1.md": "AI Fundamentals for Business",
    "2.md": "AI Prompt Engineering",
    "3.md": "AI for Daily Business Workflows",
    "4.md": "AI Image Generation for Business",
    "5.md": "AI Video Generation for Business",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_options_and_question(question_line: str) -> tuple[str, list[str]]:
    split = re.split(r"\s+[A-Da-d]\)\s*", question_line)
    question_text = clean(split[0])
    options = re.findall(
        r"[A-Da-d]\)\s*(.+?)(?=\s+[A-Da-d]\)\s*|$)",
        question_line,
    )
    options = [clean(opt) for opt in options if clean(opt)]
    return question_text, options


def parse_answers(block: str) -> list[int]:
    answers_line = re.search(r"Answers:\s*([^\n]+)", block, flags=re.IGNORECASE)
    if answers_line:
        letters = re.findall(r"[A-Da-d]", answers_line.group(1))
        return [ord(letter.lower()) - ord("a") for letter in letters]

    correct_lines = re.findall(r"Correct answer:\s*([A-Da-d])", block, flags=re.IGNORECASE)
    return [ord(letter.lower()) - ord("a") for letter in correct_lines]


def parse_quiz_questions(lesson_text: str) -> list[dict]:
    questions: list[dict] = []

    quiz_blocks = re.findall(
        r"(?:Quick Quiz|Chapter\s+\d+\s+Quiz)\s*(.*?)(?=\n(?:Practical Task|Chapter\s+\d+\s+Practical Task|Lesson\s+\d+:|Chapter\s+\d+:|$))",
        lesson_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for block in quiz_blocks:
        question_lines = re.findall(r"Question\s*\d+:\s*(.+)", block, flags=re.IGNORECASE)
        answer_indices = parse_answers(block)
        for idx, line in enumerate(question_lines):
            q_text, options = parse_options_and_question(line)
            if not q_text or len(options) < 2:
                continue
            correct_index = answer_indices[idx] if idx < len(answer_indices) else 0
            if correct_index >= len(options):
                correct_index = 0
            questions.append(
                {
                    "question": q_text,
                    "options": options,
                    "correct_index": correct_index,
                }
            )

    return questions


def extract_task_text(lesson_text: str) -> str:
    task_match = re.search(
        r"(?:Practical Task|Chapter\s+\d+\s+Practical Task)\s*(.*?)(?=\n(?:Lesson\s+\d+:|Chapter\s+\d+:|$))",
        lesson_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not task_match:
        return ""
    return task_match.group(1).strip()


def extract_blocks(lesson_text: str) -> list[dict]:
    text_without_quiz = re.sub(
        r"(?:Quick Quiz|Chapter\s+\d+\s+Quiz).*?(?=\n(?:Practical Task|Chapter\s+\d+\s+Practical Task|Lesson\s+\d+:|Chapter\s+\d+:|$))",
        "",
        lesson_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text_without_task = re.sub(
        r"(?:Practical Task|Chapter\s+\d+\s+Practical Task).*?(?=\n(?:Lesson\s+\d+:|Chapter\s+\d+:|$))",
        "",
        text_without_quiz,
        flags=re.IGNORECASE | re.DOTALL,
    )

    blocks: list[dict] = []
    for chunk in re.split(r"\n\s*\n", text_without_task):
        paragraph = chunk.strip()
        if not paragraph:
            continue
        block_type = "tip" if paragraph.lower().startswith("pro tip") else "text"
        blocks.append({"type": block_type, "content": paragraph})

    return blocks


def section_for_position(chapters: list[tuple[int, str]], position: int) -> str:
    current = "General"
    for chapter_pos, chapter_name in chapters:
        if chapter_pos <= position:
            current = chapter_name
        else:
            break
    return current


def parse_lessons(markdown_text: str) -> list[dict]:
    chapters = [
        (match.start(), clean(match.group(1)))
        for match in re.finditer(r"^Chapter\s+\d+\s*:\s*(.+)$", markdown_text, flags=re.MULTILINE)
    ]

    lesson_matches = list(
        re.finditer(r"^Lesson\s+\d+\s*:\s*(.+)$", markdown_text, flags=re.MULTILINE)
    )

    lessons: list[dict] = []

    if lesson_matches:
        for idx, match in enumerate(lesson_matches):
            lesson_title = clean(match.group(1))
            start = match.end()
            end = lesson_matches[idx + 1].start() if idx + 1 < len(lesson_matches) else len(markdown_text)
            lesson_body = markdown_text[start:end].strip()
            section_name = section_for_position(chapters, match.start())
            quiz_questions = parse_quiz_questions(lesson_body)
            lessons.append(
                {
                    "title": lesson_title,
                    "section_name": section_name,
                    "blocks": extract_blocks(lesson_body),
                    "mini_quiz": quiz_questions[:3],
                    "quiz": quiz_questions,
                    "task_text": extract_task_text(lesson_body),
                }
            )
        return lessons

    for idx, (chapter_pos, chapter_name) in enumerate(chapters):
        start = chapter_pos
        end = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(markdown_text)
        chapter_body = markdown_text[start:end].strip()
        quiz_questions = parse_quiz_questions(chapter_body)
        lessons.append(
            {
                "title": chapter_name,
                "section_name": chapter_name,
                "blocks": extract_blocks(chapter_body),
                "mini_quiz": quiz_questions[:3],
                "quiz": quiz_questions,
                "task_text": extract_task_text(chapter_body),
            }
        )

    return lessons


def build_courses_from_markdown() -> list[dict]:
    if not COURSES_DIR.exists():
        raise FileNotFoundError(f"Courses directory not found: {COURSES_DIR}")

    courses: list[dict] = []
    for md_file in sorted(COURSES_DIR.glob("*.md"), key=lambda p: p.name):
        content = md_file.read_text(encoding="utf-8")
        first_non_empty = next((line.strip() for line in content.splitlines() if line.strip()), md_file.stem)
        fallback_name = re.sub(r"^[#\s]+", "", first_non_empty)
        course_name = COURSE_NAME_BY_FILE.get(md_file.name, fallback_name)
        course_description = f"Imported from {md_file.name}"

        lessons = parse_lessons(content)
        if not lessons:
            continue

        courses.append(
            {
                "name": course_name,
                "description": course_description,
                "lessons": lessons,
            }
        )

    return courses


async def seed_database(reset: bool = False) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    parsed_courses = build_courses_from_markdown()
    if not parsed_courses:
        print("No markdown courses were parsed. Nothing to import.")
        await engine.dispose()
        return

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        if reset:
            await session.execute(delete(Course))
            await session.commit()
            print("Existing courses removed.")

        created_lessons = 0
        created_quizzes = 0

        for course_index, course_data in enumerate(parsed_courses):
            course = Course(
                name=course_data["name"],
                description=course_data["description"],
                order_index=course_index,
            )
            session.add(course)
            await session.flush()

            for lesson_index, lesson_data in enumerate(course_data["lessons"]):
                lesson = Lesson(
                    course_id=course.id,
                    title=lesson_data["title"],
                    content="\n\n".join(block["content"] for block in lesson_data["blocks"] if block["type"] == "text"),
                    section_name=lesson_data.get("section_name", "General"),
                    youtube_url=None,
                    image_urls=[],
                    task_text=lesson_data.get("task_text", ""),
                    blocks=lesson_data.get("blocks", []),
                    mini_quiz=lesson_data.get("mini_quiz", []),
                    order_index=lesson_index,
                )
                session.add(lesson)
                await session.flush()
                created_lessons += 1

                quiz_questions = lesson_data.get("quiz", [])
                if quiz_questions:
                    session.add(Quiz(lesson_id=lesson.id, questions=quiz_questions))
                    created_quizzes += 1

        await session.commit()
        print("Database seeded successfully.")
        print(f"Created courses: {len(parsed_courses)}")
        print(f"Created lessons: {created_lessons}")
        print(f"Created quizzes: {created_quizzes}")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DB from markdown courses")
    parser.add_argument("--reset", action="store_true", help="Delete existing courses before import")
    args = parser.parse_args()

    print("Seeding database from ./courses markdown files...")
    asyncio.run(seed_database(reset=args.reset))
