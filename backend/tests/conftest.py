"""Общие настройки тестов."""

import os

# Тестам не нужен настоящий пароль: база данных в них подменяется.
# Значения задаются до импорта приложения, чтобы настройки их подхватили.
os.environ.setdefault("POSTGRES_PASSWORD", "not-a-real-password")
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    # raise_server_exceptions=False: вместо падения теста получаем ответ 500,
    # как его увидел бы настоящий клиент.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# --- Тесты, которым нужна база данных -------------------------------------------
from app.core.config import get_settings  # noqa: E402
from app.core.rate_limit import (  # noqa: E402
    ai_teacher_rate_limiter,
    login_rate_limiter,
    trainer_sql_rate_limiter,
)
from app.db.session import get_db  # noqa: E402
from tests.fixtures.database import db_session, test_engine  # noqa: E402, F401


@pytest.fixture
def api_client(db_session):  # noqa: F811 — фикстура с тем же именем, так задумано
    """Клиент API, работающий с тестовой базой.

    Запросы идут «как из браузера с сайта»: с заголовком Origin адреса frontend.
    Всё, что тест записал в базу, откатывается после него.
    """
    app.dependency_overrides[get_db] = lambda: db_session
    login_rate_limiter.clear()
    ai_teacher_rate_limiter.clear()
    trainer_sql_rate_limiter.clear()
    origin = get_settings().cors_origin_list[0]
    with TestClient(app, headers={"Origin": origin}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    login_rate_limiter.clear()
    ai_teacher_rate_limiter.clear()
    trainer_sql_rate_limiter.clear()
