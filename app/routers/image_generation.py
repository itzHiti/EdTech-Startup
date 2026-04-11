from fastapi import APIRouter, HTTPException, status

from app.schemas.schemas import ImageGenerationRequest, ImageGenerationResponse
from app.services.gemini_image_service import GeminiImageGenerationError, generate_image

router = APIRouter(prefix="/image-generation", tags=["Image Generation"])


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image_route(payload: ImageGenerationRequest):
    try:
        result = await generate_image(
            model_id=payload.model,
            prompt=payload.prompt,
            aspect_ratio=payload.aspect_ratio,
            quality=payload.quality,
            images=[image.model_dump() for image in payload.images],
        )
        return result
    except GeminiImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc