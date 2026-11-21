from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from app.api.deps import get_client_ip
from app.api.endpoints.auth import get_login_rate_limiter
from app.core.config import Settings, get_settings
from app.core.rate_limit import FailureRateLimiter
from app.core.security import hash_session_token
from app.models import User, UserSession
from app.services import auth_service
from tests.api.helpers import COOKIE_NAME, PASSWORD, login, register


def _session_count(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(UserSession))


# --- Регистрация ---------------------------------------------------------------


def test_register_creates_student_and_logs_in(api_client, db_session):
    response = register(api_client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "student@example.com"
    assert body["role"] == "student"
    assert body["is_active"] is True

    set_cookie = response.headers["set-cookie"].lower()
    assert set_cookie.startswith(f"{COOKIE_NAME}=")
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/" in set_cookie
    assert "max-age=604800" in set_cookie
    # В разработке и тестах сайт работает по HTTP, поэтому без Secure.
    assert "secure" not in set_cookie

    me = api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json() == {
        "id": body["id"],
        "email": "student@example.com",
        "role": "student",
        "session_id": me.json()["session_id"],
        "session_token": None,
    }
    assert me.json()["session_id"]

    profile = api_client.get("/api/v1/users/me")
    assert profile.status_code == 200
    assert profile.json()["email"] == "student@example.com"


def test_only_token_hash_is_stored(api_client, db_session):
    register(api_client)
    token = api_client.cookies[COOKIE_NAME]

    session = db_session.scalar(select(UserSession))
    assert session.token_hash == hash_session_token(token)
    assert token not in session.token_hash
    assert len(session.token_hash) == 64


def test_password_is_stored_as_argon2_hash(api_client, db_session):
    register(api_client)

    user = db_session.scalar(select(User))
    assert user.password_hash.startswith("$argon2")
    assert PASSWORD not in user.password_hash


def test_register_normalizes_email(api_client, db_session):
    response = register(api_client, email="  Student@Example.COM ")

    assert response.status_code == 201
    assert response.json()["email"] == "student@example.com"


def test_register_duplicate_email_in_other_case_is_conflict(api_client):
    register(api_client, email="user@example.com")

    response = register(api_client, email="User@Example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_short_password_is_validation_error(api_client):
    response = register(api_client, password="short7!")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "body.password"
    # Введённый пароль не возвращается в тексте ошибки.
    assert "short7!" not in response.text


@pytest.mark.parametrize("email", ["not-an-email", "a@b", "two words@example.com", ""])
def test_register_invalid_email_is_validation_error(api_client, email):
    response = register(api_client, email=email)

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.email"


def test_email_with_control_character_is_rejected_not_crashing(api_client):
    # PostgreSQL не принимает управляющие символы в тексте: проверка должна
    # вернуть понятную ошибку 422, а не упасть с 500 на вставке.
    response = register(api_client, email="bad\u0001@example.com")

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.email"


# --- Вход ------------------------------------------------------------------------


def test_login_succeeds_and_sets_cookie(api_client):
    register(api_client)
    api_client.cookies.clear()

    response = login(api_client, email="STUDENT@example.com")

    assert response.status_code == 200
    assert response.json()["email"] == "student@example.com"
    assert COOKIE_NAME in response.cookies
    assert api_client.get("/api/v1/auth/me").status_code == 200


def test_login_wrong_password_is_unauthorized(api_client):
    register(api_client)
    api_client.cookies.clear()

    response = login(api_client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert "set-cookie" not in response.headers


def test_login_does_not_reveal_whether_email_exists(api_client):
    register(api_client)
    api_client.cookies.clear()

    wrong_password = login(api_client, password="wrong-password")
    unknown_email = login(api_client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_login_inactive_user_is_forbidden(api_client, db_session):
    register(api_client)
    api_client.cookies.clear()
    db_session.execute(update(User).values(is_active=False))

    response = login(api_client)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert "set-cookie" not in response.headers


def test_sixth_failed_login_is_rate_limited(api_client):
    register(api_client)
    api_client.cookies.clear()

    statuses = [login(api_client, password="wrong-password").status_code for _ in range(6)]

    assert statuses == [401, 401, 401, 401, 401, 429]

    # Пока действует блокировка, не пускает даже верный пароль.
    blocked = login(api_client)
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "too_many_requests"
    assert int(blocked.headers["retry-after"]) > 0


def test_rate_limit_is_per_email(api_client):
    register(api_client)
    register(api_client, email="other@example.com")
    api_client.cookies.clear()
    for _ in range(5):
        login(api_client, password="wrong-password")

    assert login(api_client, email="other@example.com").status_code == 200


# --- Сессия и выход --------------------------------------------------------------


def test_me_without_session_is_unauthorized(api_client):
    for path in ("/api/v1/auth/me", "/api/v1/users/me"):
        response = api_client.get(path)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"


def test_unknown_token_is_unauthorized(api_client):
    api_client.cookies.set(COOKIE_NAME, "made-up-token")

    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_expired_session_is_unauthorized(api_client, db_session):
    register(api_client)
    db_session.execute(
        update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_deactivated_user_loses_access(api_client, db_session):
    register(api_client)
    db_session.execute(update(User).values(is_active=False))

    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_logout_deletes_session_without_touching_new_cookie(api_client, db_session):
    register(api_client)
    token = api_client.cookies[COOKIE_NAME]
    assert _session_count(db_session) == 1

    response = api_client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    # Cookie не очищается намеренно: запоздалый ответ старой вкладки
    # не должен удалить cookie нового входа.
    assert "set-cookie" not in response.headers
    assert _session_count(db_session) == 0
    assert api_client.get("/api/v1/auth/me").status_code == 401

    # Даже если старый токен кто-то сохранил, он больше не работает.
    api_client.cookies.set(COOKIE_NAME, token)
    assert api_client.get("/api/v1/auth/me").status_code == 401


def test_logout_without_session_is_ok(api_client):
    assert api_client.post("/api/v1/auth/logout").status_code == 204


# --- Хэш пароля не попадает в ответы ---------------------------------------------


def test_password_hash_is_never_returned(api_client, db_session):
    responses = [register(api_client)]
    password_hash = db_session.scalar(select(User.password_hash))
    responses += [
        api_client.get("/api/v1/auth/me"),
        api_client.get("/api/v1/users/me"),
        login(api_client),
        register(api_client),  # 409
        login(api_client, password="wrong-password"),  # 401
    ]

    for response in responses:
        assert "password" not in response.text
        assert password_hash not in response.text
        assert PASSWORD not in response.text


def test_registration_rolls_back_when_session_cannot_be_created(
    api_client, db_session, monkeypatch
):
    def fail_token_generation() -> str:
        raise RuntimeError("генератор токена недоступен")

    monkeypatch.setattr(auth_service, "generate_session_token", fail_token_generation)

    with pytest.raises(RuntimeError):
        register(api_client)

    # Регистрация либо целиком, либо никак: пользователя без сессии не осталось.
    assert db_session.scalar(select(func.count()).select_from(User)) == 0

    # После отказа email свободен: повторная попытка создаёт аккаунт, а не 409.
    monkeypatch.undo()
    assert register(api_client).status_code == 201


def test_registration_creates_user_and_session_together(api_client, db_session):
    response = register(api_client)

    assert response.status_code == 201
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert db_session.scalar(select(func.count()).select_from(UserSession)) == 1


# --- Несколько сессий и их срок жизни ---------------------------------------------


def test_each_login_creates_its_own_session(api_client, db_session):
    register(api_client)
    api_client.cookies.clear()
    before = _session_count(db_session)

    login(api_client)
    login(api_client)

    assert _session_count(db_session) == before + 2


def test_session_lifetime_is_seven_days(api_client, db_session):
    register(api_client)

    expires_at = db_session.scalar(select(UserSession.expires_at))
    remaining = expires_at - datetime.now(UTC)

    assert timedelta(days=7) - timedelta(minutes=1) < remaining <= timedelta(days=7)


def test_login_removes_only_expired_sessions(api_client, db_session):
    first = register(api_client).json()["id"]
    second = register(api_client, email="other@example.com").json()["id"]
    # Сессия второго пользователя просрочена, у первого — ещё действует.
    db_session.execute(
        update(UserSession)
        .where(UserSession.user_id == second)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )

    api_client.cookies.clear()
    login(api_client)

    def sessions_of(user_id: int) -> int:
        return db_session.scalar(
            select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
        )

    assert sessions_of(second) == 0
    # Сессия, созданная при регистрации, и новая после входа.
    assert sessions_of(first) == 2
    # Просроченных сессий в базе не осталось.
    expired = db_session.scalar(
        select(func.count())
        .select_from(UserSession)
        .where(UserSession.expires_at <= datetime.now(UTC))
    )
    assert expired == 0


def test_logout_removes_only_current_session(api_client, db_session):
    register(api_client)
    earlier_token = api_client.cookies[COOKIE_NAME]
    login(api_client)
    current_token = api_client.cookies[COOKIE_NAME]
    assert earlier_token != current_token
    assert _session_count(db_session) == 2

    assert api_client.post("/api/v1/auth/logout").status_code == 204

    # Завершилась именно текущая сессия, а прежняя продолжает работать.
    api_client.cookies.set(COOKIE_NAME, current_token)
    assert api_client.get("/api/v1/auth/me").status_code == 401
    api_client.cookies.set(COOKIE_NAME, earlier_token)
    assert api_client.get("/api/v1/auth/me").status_code == 200
    assert _session_count(db_session) == 1


# --- Ограничение попыток: ключ «адрес клиента + email» ----------------------------


def test_failed_attempts_are_counted_per_ip_and_email(api_client):
    limiter = FailureRateLimiter(max_failures=5, window_seconds=900)
    api_client.app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    register(api_client)
    api_client.cookies.clear()

    def from_ip(address: str) -> None:
        api_client.app.dependency_overrides[get_client_ip] = lambda: address

    from_ip("10.0.0.1")
    for _ in range(5):
        login(api_client, password="wrong-password")
    assert limiter.retry_after("10.0.0.1|student@example.com") > 0

    # С другого адреса тот же email ещё не заблокирован...
    from_ip("10.0.0.2")
    assert login(api_client, password="wrong-password").status_code == 401
    # ...а с адреса перебора — заблокирован, даже с верным паролем.
    from_ip("10.0.0.1")
    assert login(api_client).status_code == 429


def test_attempt_is_counted_before_password_verification(api_client, monkeypatch):
    limiter = FailureRateLimiter(max_failures=5, window_seconds=900)
    api_client.app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    register(api_client)
    api_client.cookies.clear()

    def explode(db, email, password):
        raise RuntimeError("проверка пароля недоступна")

    monkeypatch.setattr(auth_service, "authenticate", explode)

    with pytest.raises(RuntimeError):
        login(api_client)

    monkeypatch.undo()

    # Сбойная попытка уже израсходовала одну из пяти: осталось четыре.
    statuses = [login(api_client, password="wrong-password").status_code for _ in range(4)]
    assert statuses == [401, 401, 401, 401]
    assert login(api_client).status_code == 429


def test_successful_login_resets_failure_counter(api_client):
    register(api_client)
    api_client.cookies.clear()
    for _ in range(4):
        login(api_client, password="wrong-password")

    assert login(api_client).status_code == 200

    # Счётчик обнулён: следующие четыре ошибки снова дают 401, а не 429.
    statuses = [login(api_client, password="wrong-password").status_code for _ in range(4)]
    assert statuses == [401, 401, 401, 401]


def test_cookie_is_secure_in_production(api_client):
    production = Settings(environment="production", postgres_password="not-used")
    api_client.app.dependency_overrides[get_settings] = lambda: production

    response = register(api_client)

    assert response.status_code == 201
    assert "secure" in response.headers["set-cookie"].lower()


def test_token_only_register_attaches_latest_session(api_client):
    issued = api_client.post(
        "/api/v1/auth/register?token_only=true",
        json={"email": "attach@example.com", "password": PASSWORD},
    )
    assert issued.status_code == 201
    assert "set-cookie" not in issued.headers
    token = issued.json()["session_token"]
    assert token

    attached = api_client.post("/api/v1/auth/attach", json={"session_token": token})
    assert attached.status_code == 200
    assert attached.json()["session_id"]
    assert api_client.get("/api/v1/auth/me").status_code == 200
