import base64
from collections.abc import Iterable

from elevenlabs.client import ElevenLabs

from app.core.config import get_settings

settings = get_settings()


class ElevenLabsGenerationError(RuntimeError):
    pass


def _normalize_audio_bytes(audio: object) -> bytes:
    if isinstance(audio, (bytes, bytearray, memoryview)):
        return bytes(audio)

    if isinstance(audio, Iterable):
        chunks: list[bytes] = []
        for chunk in audio:
            if isinstance(chunk, (bytes, bytearray, memoryview)):
                chunks.append(bytes(chunk))

        if chunks:
            return b"".join(chunks)

    raise ElevenLabsGenerationError("ElevenLabs returned empty audio stream")


async def generate_voiceover(
    *,
    text: str,
    voice_id: str,
    model_id: str,
    language_code: str,
    api_key: str | None,
) -> dict:
    effective_api_key = (api_key or "").strip() or settings.ELEVENLABS_API_KEY
    if not effective_api_key:
        raise ElevenLabsGenerationError("ELEVENLABS_API_KEY is not configured")

    elevenlabs = ElevenLabs(api_key=effective_api_key)

    try:
        audio_stream = elevenlabs.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            language_code=language_code,
        )
    except Exception as exc:  # noqa: BLE001
        raise ElevenLabsGenerationError(f"ElevenLabs request failed: {exc}") from exc

    audio_bytes = _normalize_audio_bytes(audio_stream)

    return {
        "voice_id": voice_id,
        "model_id": model_id,
        "language_code": language_code,
        "mime_type": "audio/mpeg",
        "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
    }
