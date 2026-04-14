from fastapi import APIRouter, HTTPException, status

from app.schemas.schemas import VoiceGenerationRequest, VoiceGenerationResponse
from app.services.elevenlabs_audio_service import ElevenLabsGenerationError, generate_voiceover

router = APIRouter(prefix="/audio-generation", tags=["Audio Generation"])


@router.post("/voiceover", response_model=VoiceGenerationResponse)
async def generate_voiceover_route(payload: VoiceGenerationRequest):
    try:
        return await generate_voiceover(
            text=payload.text,
            voice_id=payload.voice_id,
            model_id=payload.model_id,
            language_code=payload.language_code,
            api_key=payload.api_key,
        )
    except ElevenLabsGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
