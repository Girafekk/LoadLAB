from pydantic import BaseModel, Field

from app.schemas.user import PASSWORD_MAX_LENGTH, Email


class LoginRequest(BaseModel):
    """Данные для входа.

    Минимальная длина пароля здесь не проверяется: на любой неверный пароль
    ответ должен быть одинаковым — 401 без подсказок.
    """

    email: Email
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class AttachSessionRequest(BaseModel):
    """Привязка уже созданной серверной сессии к cookie."""

    session_token: str = Field(min_length=20, max_length=200)
