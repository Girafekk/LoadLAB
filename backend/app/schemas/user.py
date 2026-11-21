import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
EMAIL_MAX_LENGTH = 320

# Простая проверка формы адреса: «что-то@что-то.что-то», без пробелов.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    # Управляющие символы (включая NUL) PostgreSQL не принимает в тексте:
    # без этой проверки запрос упал бы с 500 вместо понятной ошибки 422.
    has_control_chars = any(ord(char) < 32 or ord(char) == 127 for char in email)
    if len(email) > EMAIL_MAX_LENGTH or has_control_chars or not _EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Некорректный адрес электронной почты")
    return email


# Email, приведённый к единому виду: без пробелов по краям и в нижнем регистре.
Email = Annotated[str, AfterValidator(_normalize_email)]


class UserCreate(BaseModel):
    """Данные для регистрации."""

    email: Email
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class SessionUser(BaseModel):
    """Кто сейчас вошёл: минимум, нужный интерфейсу."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: Literal["student", "admin"]
    # Идентификатор серверной сессии: позволяет отличить повторный вход
    # того же пользователя от обычной фоновой сверки.
    session_id: str | None = None


class UserRead(SessionUser):
    """Профиль пользователя. Хэша пароля здесь нет и быть не должно."""

    is_active: bool
    created_at: datetime
