"""Пароли и токены сессий.

Пароли хранятся только в виде хэша Argon2. Токен сессии выдаётся клиенту
в cookie, а в базе лежит только его SHA-256.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Превращает пароль в хэш Argon2. Обратно получить пароль из хэша нельзя."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет, что пароль соответствует сохранённому хэшу."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Хэш несуществующего пароля. Когда пользователя с таким email нет, пароль всё равно
# сверяется с этим хэшем: ответ занимает столько же времени, и по скорости ответа
# нельзя понять, зарегистрирован ли email.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def generate_session_token() -> str:
    """Случайный токен, который получит браузер."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """SHA-256 токена (64 шестнадцатеричных символа) — то, что хранится в базе."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
