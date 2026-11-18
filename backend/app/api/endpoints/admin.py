"""Административное API.

Пока здесь один служебный маршрут — для проверки разграничения прав.
Настоящая административная панель появится на отдельном этапе.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin

# Зависимость на уровне роутера: любой будущий маршрут /admin/... защищён автоматически.
router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get(
    "/ping",
    summary="Проверка прав администратора",
    description="Отвечает только администратору. Ученику — 403, без входа — 401.",
)
def ping() -> dict[str, str]:
    return {"status": "ok"}
