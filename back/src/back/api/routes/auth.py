from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from back.api.deps import get_current_user
from back.core.security import create_access_token, hash_password, verify_password
from back.db.models import User
from back.db.session import get_session
from back.schemas.auth import (
    LoginRequest,
    OnboardingBrief,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from back.services.onboarding import build_state, get_profile

router = APIRouter(prefix="/auth", tags=["auth"])


async def _token_response(session: AsyncSession, user: User) -> TokenResponse:
    profile = await get_profile(session, user)
    state = build_state(profile)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        user=UserOut.model_validate(user),
        onboarding=OnboardingBrief(completed=state.completed, next_step=state.next_step),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    existing = (
        await session.execute(select(User).where(User.login == payload.login))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Логин уже занят")
    user = User(login=payload.login, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return await _token_response(session, user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = (
        await session.execute(select(User).where(User.login == payload.login))
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    return await _token_response(session, user)


@router.get("/me", response_model=TokenResponse)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    return await _token_response(session, user)
