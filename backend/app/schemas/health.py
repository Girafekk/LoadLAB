from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = Field(description="Backend запущен и отвечает на запросы")
    service: str = Field(description="Название сервиса")
    version: str = Field(description="Версия backend")
    environment: str = Field(description="Окружение: development, test или production")
    database: Literal["ok", "unavailable"] = Field(description="Доступна ли база данных")
    timestamp: datetime = Field(description="Время ответа сервера (UTC)")
