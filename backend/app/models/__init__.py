"""Модели SQLAlchemy (таблицы базы данных).

Каждую новую модель нужно импортировать в этом файле — тогда Alembic
увидит её при создании миграций.
"""

from app.models.course import Course
from app.models.lesson import Lesson
from app.models.lesson_block import LessonBlock
from app.models.module import Module
from app.models.user import User

__all__ = ["Course", "Lesson", "LessonBlock", "Module", "User"]
