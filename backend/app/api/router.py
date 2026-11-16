"""Главный маршрутизатор API версии 1.

Каждая область (health, а в будущем auth, users, courses, lessons, quizzes,
ai, admin) живёт в своём файле в папке `endpoints` и подключается здесь
одной строкой.
"""

from fastapi import APIRouter

from app.api.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Служебные"])
