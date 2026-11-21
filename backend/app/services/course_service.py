"""Программа и опубликованное содержимое курса."""

import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.curriculum_data import COURSE
from app.models import Course, Lesson, Module
from app.schemas.course import (
    CourseOverview,
    LessonBlockRead,
    LessonBrief,
    LessonProgressState,
    LessonRead,
    ModuleRead,
)
from app.services import progress_service

_GUEST_CACHE_LOCK = threading.Lock()
_GUEST_CACHE: tuple[float, CourseOverview] | None = None
_GUEST_CACHE_TTL = 60.0


def get_course_overview(db: Session, user_id: int | None) -> CourseOverview | None:
    global _GUEST_CACHE
    if user_id is None and get_settings().is_production:
        with _GUEST_CACHE_LOCK:
            cached = _GUEST_CACHE
        if cached is not None and cached[0] > time.monotonic():
            return cached[1]

    course = db.scalar(
        select(Course)
        .where(Course.slug == COURSE.slug, Course.is_published.is_(True))
        .options(selectinload(Course.modules).selectinload(Module.lessons))
    )
    if course is None:
        return None
    ids = [item.id for module in course.modules for item in module.lessons if item.is_published]
    progress = None
    completed: set[int] = set()
    if user_id is not None:
        ordered = progress_service.completions(db, user_id, ids)
        completed = set(ordered)
        progress = LessonProgressState(
            completed_lessons=len(completed),
            total_lessons=len(ids),
            percent=(100 * len(completed)) // len(ids) if ids else 0,
            next_lesson_id=next((item for item in ids if item not in completed), None),
            last_completed_lesson_id=ordered[0] if ordered else None,
        )
    overview = CourseOverview(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        progress=progress,
        modules=[
            ModuleRead(
                id=module.id,
                title=module.title,
                summary=module.summary,
                position=module.position,
                lessons=[
                    LessonBrief(
                        id=item.id,
                        title=item.title,
                        position=item.position,
                        estimated_minutes=item.estimated_minutes,
                        is_completed=item.id in completed,
                    )
                    for item in module.lessons
                    if item.is_published
                ],
            )
            for module in course.modules
        ],
    )
    if user_id is None and get_settings().is_production:
        with _GUEST_CACHE_LOCK:
            _GUEST_CACHE = (time.monotonic() + _GUEST_CACHE_TTL, overview)
    return overview


def published_lesson(db: Session, lesson_id: int, *, include_blocks: bool = False) -> Lesson | None:
    query = (
        select(Lesson)
        .join(Module)
        .join(Course)
        .where(Lesson.id == lesson_id, Lesson.is_published.is_(True), Course.is_published.is_(True))
    )
    if include_blocks:
        query = query.options(selectinload(Lesson.blocks))
    return db.scalar(query)


def get_lesson(db: Session, user_id: int, lesson_id: int) -> LessonRead | None:
    lesson = published_lesson(db, lesson_id, include_blocks=True)
    if lesson is None:
        return None
    return LessonRead(
        id=lesson.id,
        title=lesson.title,
        summary=lesson.summary,
        estimated_minutes=lesson.estimated_minutes,
        is_completed=bool(progress_service.completions(db, user_id, [lesson_id])),
        blocks=[LessonBlockRead.model_validate(block) for block in lesson.blocks],
    )
