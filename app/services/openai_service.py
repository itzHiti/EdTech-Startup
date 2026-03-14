# app/services/openai_service.py

import json
import logging
import time

from openai import AsyncOpenAI
from app.core.config import get_settings
from app.schemas.schemas import PromptType

settings = get_settings()
logger = logging.getLogger(__name__)

# Lazily configure OpenAI client – if the API key is missing, we fall back to
# simple local behavior so that prompts can still be created in development.
if settings.OPENAI_API_KEY:
    client: AsyncOpenAI | None = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
else:
    client = None
    logger.warning(
        "OPENAI_API_KEY is not set; using local prompt assembly/naming. "
        "Set OPENAI_API_KEY in your environment to enable OpenAI-powered prompts."
    )


# ── Per-type system prompts ───────────────────────────────────────────────────

_ASSEMBLE_SYSTEM_PROMPTS: dict[PromptType, str] = {
    PromptType.image: (
        "You are a prompt engineer specializing in AI image generation (Stable Diffusion, Midjourney, DALL-E). "
        "Combine the provided blocks into a single, detailed image generation prompt. "
        "Focus on visual elements: subject, composition, lighting, style, color palette, and mood. "
        "Output ONLY the final prompt text, no explanation."
    ),
    PromptType.video: (
        "You are a prompt engineer specializing in AI video generation (Sora, Runway, Kling). "
        "Combine the provided blocks into a single, detailed video generation prompt. "
        "Focus on scene, motion, camera movement, transitions, pacing, and temporal flow. "
        "Output ONLY the final prompt text, no explanation."
    ),
    PromptType.text: (
        "You are a prompt engineer specializing in LLM text generation prompts. "
        "Combine the provided blocks into a single, well-structured text generation prompt. "
        "Focus on tone, audience, format, style, and content goals. "
        "Output ONLY the final prompt text, no explanation."
    ),
}


# ── Quiz generation (unchanged) ───────────────────────────────────────────────

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

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0].strip()

        questions = json.loads(raw)

        if not isinstance(questions, list) or len(questions) != 3:
            logger.error("Invalid quiz format returned: %s", raw)
            raise ValueError("Model returned incorrect number of questions")

        logger.info("Quiz generated successfully in %.2f seconds", time.time() - start)
        return questions

    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from model response")
        raise
    except Exception:
        logger.exception("OpenAI quiz generation failed")
        raise


# ── Prompt assembly (type-aware) ──────────────────────────────────────────────

async def _assemble_prompt_local(blocks: list[dict], prompt_type: PromptType) -> str:
    """Simple offline fallback: concatenate blocks into a readable prompt."""

    parts = [f"{b['type'].strip()}: {b['value'].strip()}" for b in blocks]
    joined = "; ".join(parts)
    return f"{prompt_type.value.capitalize()} prompt – {joined}"


async def assemble_prompt(blocks: list[dict], prompt_type: PromptType) -> str:
    """Combine user-defined blocks into a coherent prompt for the given type.

    If OpenAI is not configured or fails, we fall back to a deterministic
    local implementation so that prompt creation still succeeds.
    """

    start = time.time()
    logger.info(
        "Assembling %s prompt from %d blocks",
        prompt_type.value,
        len(blocks),
    )

    # Fallback path when no OpenAI client is configured
    if client is None:
        result = await _assemble_prompt_local(blocks, prompt_type)
        logger.info(
            "%s prompt assembled locally in %.2f seconds (no OpenAI client)",
            prompt_type.value,
            time.time() - start,
        )
        return result

    block_descriptions = "\n".join(
        f"- {b['type']}: {b['value']}" for b in blocks
    )

    system_prompt = _ASSEMBLE_SYSTEM_PROMPTS[prompt_type]

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Combine these blocks into a {prompt_type.value} prompt:\n"
                        f"{block_descriptions}"
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=500,
        )

        result = response.choices[0].message.content.strip()
        logger.debug("Generated %s prompt: %s", prompt_type.value, result)
        logger.info(
            "%s prompt assembled via OpenAI in %.2f seconds",
            prompt_type.value,
            time.time() - start,
        )
        return result

    except Exception:
        logger.exception(
            "Prompt assembly via OpenAI failed for type: %s. Falling back to local assembly.",
            prompt_type.value,
        )
        result = await _assemble_prompt_local(blocks, prompt_type)
        logger.info(
            "%s prompt assembled locally in %.2f seconds after OpenAI failure",
            prompt_type.value,
            time.time() - start,
        )
        return result


# ── Prompt naming (type-agnostic) ─────────────────────────────────────────────

async def _name_prompt_local(final_prompt: str) -> str:
    """Offline fallback for prompt naming – derive a short name from the prompt."""

    words = [w for w in final_prompt.split() if w.strip()]
    if not words:
        return "Untitled Prompt"
    return " ".join(words[:3])


async def name_prompt(final_prompt: str) -> str:
    """Generate a 2-3 word name for a saved prompt.

    If OpenAI is not configured or fails, we fall back to deriving a short
    name locally from the prompt text.
    """

    start = time.time()
    logger.info("Generating prompt name")

    # Fallback path when no OpenAI client is configured
    if client is None:
        name = await _name_prompt_local(final_prompt)
        logger.info(
            "Prompt name generated locally in %.2f seconds: %s (no OpenAI client)",
            time.time() - start,
            name,
        )
        return name

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a concise 2-3 word name for the following "
                        "prompt. Output ONLY the name, no punctuation."
                    ),
                },
                {"role": "user", "content": final_prompt},
            ],
            temperature=0.5,
            max_tokens=20,
        )

        name = response.choices[0].message.content.strip()
        logger.info(
            "Prompt name generated via OpenAI in %.2f seconds: %s",
            time.time() - start,
            name,
        )
        return name

    except Exception:
        logger.exception(
            "Prompt naming via OpenAI failed; falling back to local naming."
        )
        name = await _name_prompt_local(final_prompt)
        logger.info(
            "Prompt name generated locally in %.2f seconds: %s",
            time.time() - start,
            name,
        )
        return name