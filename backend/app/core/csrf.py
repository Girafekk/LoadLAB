"""Защита от CSRF — подделки запросов с чужих сайтов.

Браузер сам прикладывает cookie к запросам на наш адрес, даже если запрос
отправила посторонняя страница. Поэтому для запросов, которые что-то меняют,
проверяется заголовок Origin: браузер пишет в него адрес страницы-отправителя,
и подделать его скрипт не может. Вместе с cookie SameSite=Lax этого достаточно.
"""

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def verify_origin(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """Пропускает изменяющий запрос, только если он пришёл с разрешённого адреса.

    Разрешены адреса frontend из CORS_ORIGINS и адрес самого API — чтобы
    запросы можно было отправлять со страницы документации /api/v1/docs.
    """
    if request.method in SAFE_METHODS:
        return

    origin = request.headers.get("origin")
    own_origin = f"{request.url.scheme}://{request.url.netloc}"
    if origin is None or (origin != own_origin and origin not in settings.cors_origin_list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Запрос отправлен с неразрешённого адреса",
        )
