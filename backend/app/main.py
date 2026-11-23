"""Точка входа backend: здесь создаётся и настраивается приложение FastAPI.

Запуск для разработки (из папки backend):

    uvicorn app.main:app --reload --port 8001
"""

import json
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers


class UploadLimitMiddleware:
    """Ограничивает фактические байты загрузки до multipart-парсера."""

    def __init__(self, app, limit: int = 11 * 1024 * 1024) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].rstrip("/") not in {
            "/api/v1/admin/interview/sources",
            "/api/v1/admin/course-imports/preview",
        }:
            await self.app(scope, receive, send)
            return
        if scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            body.extend(message.get("body", b""))
            if len(body) > self.limit:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps(
                            {
                                "error": {
                                    "code": "http_error",
                                    "message": "Файл больше 10 МБ",
                                    "details": None,
                                }
                            },
                            ensure_ascii=False,
                        ).encode(),
                    }
                )
                return
            if not message.get("more_body", False):
                break
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {
                "type": "http.request",
                "body": bytes(body),
                "more_body": False,
            }

        await self.app(scope, replay_receive, send)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API образовательной платформы LoadLab.",
        # Документация OpenAPI: Swagger UI, ReDoc и «сырая» схема.
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    )

    app.add_middleware(UploadLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Session-Changed"],
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
