"""Настройки приложения.

Все значения читаются из переменных окружения или из файла `.env`
в корне проекта. Секреты (например, пароль базы данных) в коде не хранятся.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# backend/app/core/config.py -> корень проекта находится на три уровня выше.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Приложение ---
    app_name: str = "LoadLab API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    # Адреса frontend, которым разрешено обращаться к API из браузера (через запятую).
    cors_origins: str = "http://localhost:3000"

    # Имя cookie, в которой браузер хранит токен сессии.
    session_cookie_name: str = "loadlab_session"

    # --- AI Teacher ---
    # Если base_url и api_key заданы, используется OpenAI-совместимый сервис.
    # Без них AI Teacher работает в локальном режиме по материалу урока.
    ai_teacher_base_url: str | None = None
    ai_teacher_api_key: str | None = None
    ai_teacher_model: str = "gpt-4o-mini"

    # --- База данных PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "loadlab"
    postgres_user: str = "loadlab"
    # Значения по умолчанию нет намеренно: пароль задаётся только в .env.
    postgres_password: str

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url(self) -> URL:
        """Адрес подключения к базе данных для SQLAlchemy (драйвер psycopg 3)."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    """Возвращает настройки. Результат кэшируется: `.env` читается один раз."""
    return Settings()
