"""Users API router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate

router = APIRouter()


@router.post("/")
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # TODO: implement
    return {"message": "User created", "email": user.email}


@router.get("/me")
async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Get current user profile."""
    # TODO: implement auth
    return {"message": "Not implemented"}
