import json
import logging
import time

from openai import AsyncOpenAI
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_quiz(lesson_content: str) -> list[dict]:
    """Generate 3 multiple-choice questions from lesson content using GPT."""

    start = time.time()
    logger.info("Starting quiz generation")

    system_prompt = (
        "You are a quiz generator for an educational platform. "
        "Given lesson content, create exactly 3 multiple-choice questions. "
        "Each question must have exactly 4 options and one correct answer. "
        "Respond ONLY with a valid JSON array (no markdown, no explanation). "
        'Format: [{"question": "...", "options": ["A","B","C","D"], "correct_index": 0}]'
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Generate a quiz from this lesson:\n\n{lesson_content[:4000]}",
                },
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        raw = response.choices[0].message.content.strip()

        logger.debug("Raw model response: %s", raw)

        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0].strip()

        questions = json.loads(raw)

        if not isinstance(questions, list) or len(questions) != 3:
            logger.error("Invalid quiz format returned: %s", raw)
            raise ValueError("Model returned incorrect number of questions")

        logger.info(
            "Quiz generated successfully in %.2f seconds",
            time.time() - start
        )

        return questions

    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from model response")
        raise

    except Exception as e:
        logger.exception("OpenAI quiz generation failed: %s", str(e))
        raise


async def assemble_prompt(blocks: list[dict]) -> str:
    """Combine user-defined blocks into a coherent image generation prompt."""

    start = time.time()
    logger.info("Assembling image prompt from %d blocks", len(blocks))

    block_descriptions = "\n".join(
        f"- {b['type']}: {b['value']}" for b in blocks
    )

    system_prompt = (
        "You are a prompt engineer specializing in image generation. "
        "Combine the provided blocks into a single coherent and detailed "
        "image generation prompt. Output ONLY the final prompt."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Combine these blocks into an image prompt:\n{block_descriptions}",
                },
            ],
            temperature=0.7,
            max_tokens=500,
        )

        result = response.choices[0].message.content.strip()

        logger.debug("Generated prompt: %s", result)

        logger.info(
            "Prompt assembled successfully in %.2f seconds",
            time.time() - start
        )

        return result

    except Exception as e:
        logger.exception("Prompt assembly failed: %s", str(e))
        raise


async def name_prompt(final_prompt: str) -> str:
    """Generate a 2-3 word name for a saved prompt."""

    start = time.time()
    logger.info("Generating prompt name")

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a concise 2-3 word name for the following "
                        "image prompt. Output ONLY the name."
                    ),
                },
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.5,
            max_tokens=20,
        )

        name = response.choices[0].message.content.strip()

        logger.info(
            "Prompt name generated in %.2f seconds: %s",
            time.time() - start,
            name
        )

        return name

    except Exception as e:
        logger.exception("Prompt naming failed: %s", str(e))
        raise