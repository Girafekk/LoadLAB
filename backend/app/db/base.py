from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех моделей (таблиц) SQLAlchemy.

    Будущие модели (User, Course, Lesson, Quiz ...) наследуются от него
    и размещаются в папке `app/models`.
    """
