"""Пользователи. Пока — только собственный профиль."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models import User
from app.schemas.user import UserRead

router = APIRouter(prefix="/users")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Мой профиль",
    description="Профиль вошедшего пользователя. Без действующей сессии — 401.",
)
def read_own_profile(user: User = Depends(get_current_user)) -> User:
    return user
