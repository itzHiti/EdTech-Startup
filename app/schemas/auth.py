from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator


class GoogleLoginRequest(BaseModel):
    id_token: str


class EmailPasswordSignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str


class EmailPasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str