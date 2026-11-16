"""Проверка состояния backend."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.db.session import is_database_available
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Состояние backend",
    description=(
        "Сообщает, что backend запущен, и показывает его версию, окружение "
        "и доступность базы данных."
    ),
)
def get_health(
    settings: Settings = Depends(get_settings),
    database_available: bool = Depends(is_database_available),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database="ok" if database_available else "unavailable",
        timestamp=datetime.now(UTC),
    )
