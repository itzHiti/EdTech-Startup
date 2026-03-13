from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database.database import get_db
from app.models.models import Prompt, User
from app.core.rate_limiter import gpt_rate_limiter
from app.schemas import PromptCreate, PromptOut
from app.services.openai_service import assemble_prompt, name_prompt

router = APIRouter(prefix="/prompts", tags=["Prompt Builder"])


@router.post("/create", response_model=PromptOut)
async def create_prompt(
    payload: PromptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new image prompt from blocks.

    1. Rate-limit check
    2. Assemble blocks into a coherent prompt via GPT
    3. Auto-name the prompt via GPT
    4. Save to database
    """
    gpt_rate_limiter.check(user.id)

    blocks_data = [b.model_dump() for b in payload.blocks]
    final_prompt = await assemble_prompt(blocks_data)
    prompt_name = await name_prompt(final_prompt)

    prompt = Prompt(
        user_id=user.id,
        name=prompt_name,
        blocks=blocks_data,
        final_prompt=final_prompt,
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    return prompt


@router.get("", response_model=list[PromptOut])
async def list_prompts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's prompt history."""
    result = await db.execute(
        select(Prompt)
        .where(Prompt.user_id == user.id)
        .order_by(Prompt.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific prompt (owner only)."""
    prompt = await db.get(Prompt, prompt_id)
    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt (owner only)."""
    prompt = await db.get(Prompt, prompt_id)
    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    await db.delete(prompt)
    return {"message": "Prompt deleted"}
