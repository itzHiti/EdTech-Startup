# app/routers/prompts.py

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database.database import get_db
from app.models.models import Prompt, User
from app.core.rate_limiter import gpt_rate_limiter
from app.schemas.schemas import PromptCreate, PromptOut, PromptType, PromptUpdate
from app.services.openai_service import assemble_prompt, name_prompt

router = APIRouter(prefix="/prompts", tags=["Prompt Builder"])


@router.post("/create", response_model=PromptOut, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new prompt from blocks.

    - `prompt_type`: `image` | `video` | `text`
    - `blocks`: list of `{type, value}` pairs defined by the frontend
    """
    gpt_rate_limiter.check(user.id)

    blocks_data = [b.model_dump() for b in payload.blocks]

    # Pass type so GPT uses the correct system prompt
    final_prompt = await assemble_prompt(blocks_data, payload.prompt_type)
    prompt_name = await name_prompt(final_prompt)

    prompt = Prompt(
        user_id=user.id,
        name=prompt_name,
        prompt_type=payload.prompt_type.value,
        blocks=blocks_data,
        final_prompt=final_prompt,
    )
    db.add(prompt)
    await db.flush()
    await db.refresh(prompt)
    return prompt


@router.get("", response_model=list[PromptOut])
async def list_prompts(
    prompt_type: PromptType | None = Query(
        default=None,
        description="Filter by prompt type: image | video | text",
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all prompts for the current user.

    Optionally filter with `?prompt_type=image` / `video` / `text`.
    """
    query = (
        select(Prompt)
        .where(Prompt.user_id == user.id)
        .order_by(Prompt.created_at.desc())
    )

    if prompt_type is not None:
        query = query.where(Prompt.prompt_type == prompt_type.value)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific prompt by ID (owner only)."""
    prompt = await db.get(Prompt, prompt_id)

    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
    return prompt


@router.put("/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    prompt_id: int,
    payload: PromptUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a prompt (owner only).

    - Providing `blocks` regenerates `final_prompt` via GPT (rate-limited).
    - Providing only `name` renames without a GPT call.
    - Both fields are optional — send only what you want to change.
    """
    prompt = await db.get(Prompt, prompt_id)

    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    if payload.blocks is not None:
        # Blocks changed → regenerate via GPT
        gpt_rate_limiter.check(user.id)

        blocks_data = [b.model_dump() for b in payload.blocks]
        prompt_type = PromptType(prompt.prompt_type)  # read type from existing row

        final_prompt = await assemble_prompt(blocks_data, prompt_type)

        prompt.blocks = blocks_data
        prompt.final_prompt = final_prompt

    if payload.name is not None:
        prompt.name = payload.name

    # Manually stamp updated_at (onupdate only fires on UPDATE statements,
    # not when mutating attributes directly in a session)
    prompt.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a prompt (owner only)."""
    prompt = await db.get(Prompt, prompt_id)

    if prompt is None or prompt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    await db.delete(prompt)