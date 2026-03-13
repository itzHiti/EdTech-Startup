from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database.database import get_db
from app.models.models import User
from app.schemas import UserOut, UserUpdate

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserOut)
async def get_profile(user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return user


@router.put("", response_model=UserOut)
async def update_profile(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile (full_name only)."""
    if payload.full_name is not None:
        user.full_name = payload.full_name
    await db.flush()
    await db.refresh(user)
    return user
