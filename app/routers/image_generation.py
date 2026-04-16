from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.database.database import get_db
from app.models.models import User
from app.schemas.schemas import ImageGenerationRequest, ImageGenerationResponse
from app.services.gemini_image_service import GeminiImageGenerationError, generate_image

router = APIRouter(prefix="/image-generation", tags=["Image Generation"])
optional_bearer = HTTPBearer(auto_error=False)


async def _get_optional_user(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> User | None:
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image_route(
    payload: ImageGenerationRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_optional_user(credentials, db)

    if payload.model == "nano-banana-pro" and (user is None or not user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nano Banana Pro is available for Admin users only",
        )

    try:
        result = await generate_image(
            model_id=payload.model,
            prompt=payload.prompt,
            aspect_ratio=payload.aspect_ratio,
            quality=payload.quality,
            api_key=payload.api_key,
            images=[image.model_dump() for image in payload.images],
        )
        return result
    except GeminiImageGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc