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
