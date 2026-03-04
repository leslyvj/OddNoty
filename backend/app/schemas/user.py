"""User schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    telegram_id: Optional[str] = None


class UserResponse(BaseModel):
    user_id: int
    email: str
    telegram_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
