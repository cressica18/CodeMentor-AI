from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import User
from app.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.cf_handle == payload.cf_handle))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Handle already registered")

    user = User(cf_handle=payload.cf_handle)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{cf_handle}", response_model=UserRead)
async def get_user(cf_handle: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.cf_handle == cf_handle))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
