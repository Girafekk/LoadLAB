"""Общие зависимости маршрутов: кто отправил запрос и что ему разрешено.

Права проверяются здесь, на сервере. Проверки во frontend существуют только
для удобства пользователя и ничего не защищают.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import User
from app.services import auth_service


def get_session_token(request: Request, settings: Settings = Depends(get_settings)) -> str | None:
    """Токен сессии из cookie запроса (или None, если cookie нет)."""
    return request.cookies.get(settings.session_cookie_name)


def get_client_ip(request: Request) -> str:
    """Адрес клиента — часть ключа для ограничения попыток входа.

    Отдельная зависимость, чтобы в тестах можно было подставить любой адрес.
    """
    return request.client.host if request.client else "unknown"


def get_optional_user(
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> User | None:
    return auth_service.get_user_by_session_token(db, token) if token else None


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    """Текущий пользователь. Без действующей сессии — ошибка 401."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход в систему"
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Пропускает только администратора. Остальным — ошибка 403."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    return user
