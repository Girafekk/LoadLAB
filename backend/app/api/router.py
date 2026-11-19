"""Главный маршрутизатор API версии 1.

Каждая область (health, auth, users, admin, а в будущем courses, lessons,
quizzes, ai) живёт в своём файле в папке `endpoints` и подключается здесь
одной строкой.
"""

from fastapi import APIRouter, Depends

from app.api.endpoints import (
    admin,
    admin_content,
    ai,
    auth,
    courses,
    health,
    lessons,
    notes,
    quizzes,
    student_tools,
    trainers,
    users,
)
from app.core.csrf import verify_origin

# verify_origin защищает от CSRF все изменяющие запросы (POST, PUT, PATCH, DELETE).
api_router = APIRouter(dependencies=[Depends(verify_origin)])
api_router.include_router(health.router, tags=["Служебные"])
api_router.include_router(auth.router, tags=["Авторизация"])
api_router.include_router(users.router, tags=["Пользователи"])
api_router.include_router(admin.router, tags=["Администрирование"])
api_router.include_router(admin_content.router, tags=["Администрирование"])
api_router.include_router(courses.router, tags=["Курсы"])
api_router.include_router(lessons.router, tags=["Уроки"])
api_router.include_router(quizzes.router, tags=["Квизы"])
api_router.include_router(notes.router)
api_router.include_router(student_tools.router)
api_router.include_router(trainers.router, tags=["Тренажёры"])
api_router.include_router(ai.router, tags=["AI Teacher"])
