"""Учётные записи и сессии входа.

Сервис ничего не знает про HTTP: о проблемах он сообщает собственными
исключениями, а в коды ответа их переводят маршруты.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.rate_limit import FailureRateLimiter
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models import User, UserSession

SESSION_TTL = timedelta(days=7)


class EmailAlreadyRegisteredError(Exception):
    """Пользователь с таким email уже существует."""


class TooManyLoginAttemptsError(Exception):
    """Слишком много неудачных попыток входа: вход временно заблокирован."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Слишком много неудачных попыток входа")
        self.retry_after_seconds = retry_after_seconds


class InvalidCredentialsError(Exception):
    """Неверный email или пароль (что именно — не уточняется намеренно)."""


class InactiveUserError(Exception):
    """Учётная запись отключена."""


def normalize_email(email: str) -> str:
    """«  User@X.ru » и «user@x.ru» — один и тот же адрес."""
    return email.strip().lower()


def login_limiter_key(client_ip: str, email: str) -> str:
    """Ключ счётчика неудачных входов: адрес клиента плюс email.

    Перебор с одного адреса не должен блокировать тот же email у других людей.
    """
    return f"{client_ip}|{normalize_email(email)}"


def reserve_login_attempt(limiter: FailureRateLimiter, client_ip: str, email: str) -> None:
    """Занимает попытку входа и проверяет лимит одной операцией.

    Попытка учитывается до проверки пароля. Иначе параллельные запросы успевали
    пройти проверку лимита, пока первый из них ещё сверял хэш Argon2, и за окно
    проходило больше попыток, чем разрешено.
    """
    retry_after = limiter.reserve_attempt(login_limiter_key(client_ip, email))
    if retry_after:
        raise TooManyLoginAttemptsError(retry_after)


def clear_login_failures(limiter: FailureRateLimiter, client_ip: str, email: str) -> None:
    """Сбрасывает счётчик после успешного входа."""
    limiter.reset(login_limiter_key(client_ip, email))


def _add_user(db: Session, email: str, password: str, role: str) -> User:
    """Готовит пользователя к вставке, заранее проверяя занятость email."""
    email = normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise EmailAlreadyRegisteredError

    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    return user


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        # Два одновременных запроса с одним email: второй упирается в UNIQUE.
        db.rollback()
        raise EmailAlreadyRegisteredError from error


def register_user(db: Session, email: str, password: str, role: str = "student") -> User:
    """Создаёт пользователя без сессии. Так администратора создаёт CLI."""
    user = _add_user(db, email, password, role)
    _commit_or_conflict(db)
    return user


def register_user_with_session(db: Session, email: str, password: str) -> tuple[User, str]:
    """Создаёт ученика и его первую сессию одной транзакцией.

    Либо в базе появляются и пользователь, и сессия, либо ничего. Иначе сбой
    второй вставки оставлял созданный аккаунт, а человек видел ошибку и при
    повторе получал «email уже зарегистрирован».
    """
    user = _add_user(db, email, password, "student")
    try:
        # flush нужен, чтобы получить id пользователя до вставки сессии.
        db.flush()
        token = generate_session_token()
        db.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(token),
                expires_at=datetime.now(UTC) + SESSION_TTL,
            )
        )
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise EmailAlreadyRegisteredError from error
    except Exception:
        # Любой другой сбой (например, генератор токена) не должен оставить
        # в базе пользователя без сессии.
        db.rollback()
        raise
    return user, token


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        raise InvalidCredentialsError
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    return user


def create_session(db: Session, user: User) -> str:
    """Создаёт сессию и возвращает токен для cookie. В базу попадает только его хэш."""
    token = generate_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + SESSION_TTL,
        )
    )
    db.commit()
    return token


def get_user_by_session_token(db: Session, token: str) -> User | None:
    """Возвращает пользователя по токену из cookie, если сессия жива, а запись активна."""
    return db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.expires_at > datetime.now(UTC),
            User.is_active.is_(True),
        )
    )


def delete_session(db: Session, token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))
    db.commit()


def delete_expired_sessions(db: Session) -> None:
    db.execute(delete(UserSession).where(UserSession.expires_at <= datetime.now(UTC)))
    db.commit()
