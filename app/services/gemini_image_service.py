import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

GEMINI_MODEL_MAP = {
    "nano-banana-pro": "gemini-3-pro-image-preview",
    "nano-banana-2": "gemini-3.1-flash-image-preview",
}


class GeminiImageGenerationError(RuntimeError):
    pass


def _strip_data_url(data: str) -> tuple[str, str | None]:
    if data.startswith("data:") and "," in data:
        header, payload = data.split(",", 1)
        mime_type = None
        if ";base64" in header and header.startswith("data:"):
            mime_type = header[5 : header.index(";base64")]
        return payload, mime_type
    return data, None


def _normalize_mime_type(mime_type: str | None, fallback: str = "image/png") -> str:
    if mime_type:
        return mime_type
    return fallback


async def generate_image(
    *,
    model_id: str,
    prompt: str,
    aspect_ratio: str,
    quality: str,
    api_key: str | None,
    images: list[dict],
) -> dict:
    effective_api_key = (api_key or "").strip() or settings.GEMINI_API_KEY

    if not effective_api_key:
        raise GeminiImageGenerationError("GEMINI_API_KEY is not configured")

    model_name = GEMINI_MODEL_MAP.get(model_id)
    if model_name is None:
        raise GeminiImageGenerationError(f"Unsupported model: {model_id}")

    parts: list[dict] = [{"text": prompt}]
    for image in images:
        raw_data, mime_from_data_url = _strip_data_url(image["data"])
        parts.append(
            {
                "inlineData": {
                    "mimeType": _normalize_mime_type(image.get("mime_type") or mime_from_data_url),
                    "data": raw_data,
                }
            }
        )

    request_body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": quality,
            },
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    params = {"key": effective_api_key}

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, params=params, json=request_body)

    if response.status_code >= 400:
        logger.error("Gemini image generation failed: %s", response.text)
        raise GeminiImageGenerationError(f"Gemini API request failed with status {response.status_code}")

    payload = response.json()
    candidates = payload.get("candidates") or []
    if not candidates:
        raise GeminiImageGenerationError("Gemini API returned no candidates")

    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
    generated_images: list[dict] = []
    text_chunks: list[str] = []

    for part in parts:
        if part.get("thought"):
            continue

        text = part.get("text")
        if text:
            text_chunks.append(text)

        inline_data = part.get("inlineData") or part.get("inline_data")
        if inline_data and inline_data.get("data"):
            generated_images.append(
                {
                    "data": inline_data["data"],
                    "mime_type": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png",
                }
            )

    if not generated_images:
        raise GeminiImageGenerationError("Gemini API did not return an image")

    return {
        "model": model_id,
        "prompt": prompt,
        "images": generated_images,
        "text": "\n".join(text_chunks).strip() or None,
    }