"""Регистрация, вход, выход и «кто я»."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_session_token
from app.core.config import Settings, get_settings
from app.core.rate_limit import FailureRateLimiter, login_rate_limiter
from app.db.session import get_db
from app.models import User
from app.schemas.auth import LoginRequest
from app.schemas.user import SessionUser, UserCreate, UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth")


def get_login_rate_limiter() -> FailureRateLimiter:
    return login_rate_limiter


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=int(auth_service.SESSION_TTL.total_seconds()),
        path="/",
        # httponly: JavaScript на странице не может прочитать cookie.
        httponly=True,
        samesite="lax",
        # secure: только по HTTPS. В разработке сайт работает по HTTP.
        secure=settings.is_production,
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация",
    description="Создаёт учётную запись ученика и сразу выполняет вход.",
)
def register(
    data: UserCreate,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    try:
        # Пользователь и первая сессия создаются одной транзакцией.
        user, token = auth_service.register_user_with_session(db, data.email, data.password)
    except auth_service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже зарегистрирован",
        ) from None

    _set_session_cookie(response, token, settings)
    return user


@router.post(
    "/login",
    response_model=UserRead,
    summary="Вход",
    description=(
        "Проверяет email и пароль и ставит cookie сессии. После 5 неудачных попыток "
        "за 15 минут для пары «IP-адрес + email» вход временно блокируется."
    ),
)
def login(
    data: LoginRequest,
    response: Response,
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limiter: FailureRateLimiter = Depends(get_login_rate_limiter),
) -> User:
    try:
        # Попытка занимается до проверки пароля: иначе параллельные запросы
        # успевали пройти лимит, пока первый ещё сверял хэш.
        auth_service.reserve_login_attempt(limiter, client_ip, data.email)
    except auth_service.TooManyLoginAttemptsError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много неудачных попыток входа. Попробуйте позже",
            headers={"Retry-After": str(error.retry_after_seconds)},
        ) from None

    try:
        user = auth_service.authenticate(db, data.email, data.password)
    except auth_service.InvalidCredentialsError:
        # Не уточняем, что именно неверно: иначе можно подбирать адреса.
        # Попытка уже учтена при резервировании.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль"
        ) from None
    except auth_service.InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Учётная запись отключена"
        ) from None

    auth_service.clear_login_failures(limiter, client_ip, data.email)
    auth_service.delete_expired_sessions(db)
    _set_session_cookie(response, auth_service.create_session(db, user), settings)
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Выход",
    description="Удаляет сессию на сервере и очищает cookie.",
)
def logout(
    response: Response,
    token: str | None = Depends(get_session_token),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    if token:
        auth_service.delete_session(db, token)
    _clear_session_cookie(response, settings)


@router.get(
    "/me",
    response_model=SessionUser,
    summary="Текущий пользователь",
    description="Кто сейчас вошёл. Без действующей сессии — 401.",
)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user
