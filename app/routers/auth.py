from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.database.database import get_db
from app.models.models import User
from app.schemas.auth import (
    GoogleLoginRequest,
    EmailPasswordSignupRequest,
    EmailPasswordLoginRequest,
    TokenResponse,
    RefreshRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


@router.post("/google", response_model=TokenResponse)
async def google_login(payload: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with a Google OAuth id_token.

    The frontend obtains an id_token from Google Sign-In and sends it here.
    We verify it with Google, then create or fetch the local user and return JWTs.
    """
    # Verify the id_token with Google
    async with httpx.AsyncClient() as http:
        resp = await http.get(GOOGLE_TOKENINFO_URL, params={"id_token": payload.id_token})

    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    google_data = resp.json()

    # Validate audience matches our client id
    if google_data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

    google_id = google_data["sub"]
    email = google_data.get("email", "")
    full_name = google_data.get("name", "")

    # Find or create user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=email, full_name=full_name, google_id=google_id)
        db.add(user)
        await db.flush()
        await db.refresh(user)

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def email_password_signup(
    payload: EmailPasswordSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email and password."""
    # Check if the email is already in use
    result = await db.execute(select(User).where(User.email == payload.email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        google_id=None,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/login", response_model=TokenResponse)
async def email_password_login(
    payload: EmailPasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user using email and password."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Get a new access token using a refresh token."""
    decoded = decode_token(payload.refresh_token, expected_type="refresh")
    user_id = decoded.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/logout")
async def logout():
    """Logout endpoint – with stateless JWTs, the client simply discards the tokens."""
    return {"message": "Successfully logged out"}
