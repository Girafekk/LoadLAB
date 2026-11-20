"""Точка входа backend: здесь создаётся и настраивается приложение FastAPI.

Запуск для разработки (из папки backend):

    uvicorn app.main:app --reload --port 8001
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers


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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    @app.middleware("http")
    async def limit_interview_upload(request: Request, call_next):
        if request.method == "POST" and request.url.path.endswith("/admin/interview/sources"):
            length = int(request.headers.get("content-length", "0") or 0)
            if length > 11 * 1024 * 1024:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "file_too_large",
                            "message": "Файл больше 10 МБ",
                            "details": None,
                        }
                    },
                )
        return await call_next(request)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
