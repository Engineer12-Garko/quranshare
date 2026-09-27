"""Pydantic schemas for user request and response bodies."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ActivateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    gender: Literal["Male", "Female"] | None = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    gender: Literal["Male", "Female"] | None = None


class AdminUpdateUserRequest(BaseModel):
    role: Literal["user", "curator", "admin"] | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    whatsapp_number: str | None
    gender: str | None
    role: Literal["user", "curator", "admin"]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}