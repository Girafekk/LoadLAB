"""Полнотекстовый поиск по курсу, квизам и разборам."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, cast, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import InterviewQuestion, Lesson, LessonBlock, Module, Quiz, QuizQuestion

router = APIRouter(prefix="/search", tags=["Поиск"])


@router.get("", summary="Поиск по материалам")
def search(q: str = Query(min_length=2, max_length=80), db: Session = Depends(get_db)) -> dict:
    pattern = f"%{q}%"
    results: list[dict] = []

    lessons = db.execute(
        select(Lesson.id, Lesson.title, Module.title)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            Lesson.is_published.is_(True),
            or_(Lesson.title.ilike(pattern), Lesson.summary.ilike(pattern)),
        )
        .limit(20)
    ).all()
    for lesson_id, title, module_title in lessons:
        results.append(
            {
                "type": "Урок",
                "title": title,
                "context": module_title,
                "url": f"/learn/lessons/{lesson_id}",
            }
        )

    blocks = db.execute(
        select(Lesson.id, Lesson.title, Module.title)
        .join(Module, Module.id == Lesson.module_id)
        .join(LessonBlock, LessonBlock.lesson_id == Lesson.id)
        .where(
            Lesson.is_published.is_(True),
            cast(LessonBlock.content, Text).ilike(pattern),
        )
        .distinct()
        .limit(20)
    ).all()
    for lesson_id, title, module_title in blocks:
        results.append(
            {
                "type": "Материал урока",
                "title": title,
                "context": module_title,
                "url": f"/learn/lessons/{lesson_id}",
            }
        )

    questions = db.execute(
        select(QuizQuestion.id, QuizQuestion.text, Lesson.id, Lesson.title)
        .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
        .join(Lesson, Lesson.id == Quiz.lesson_id)
        .where(
            Lesson.is_published.is_(True),
            or_(QuizQuestion.text.ilike(pattern), QuizQuestion.explanation.ilike(pattern)),
        )
        .limit(20)
    ).all()
    for _question_id, text, lesson_id, lesson_title in questions:
        results.append(
            {
                "type": "Вопрос квиза",
                "title": text[:160],
                "context": lesson_title,
                "url": f"/learn/lessons/{lesson_id}",
            }
        )

    interview = db.scalars(
        select(InterviewQuestion)
        .where(
            InterviewQuestion.status == "approved",
            or_(
                InterviewQuestion.text.ilike(pattern),
                InterviewQuestion.reference_answer.ilike(pattern),
            ),
        )
        .limit(20)
    ).all()
    for item in interview:
        results.append(
            {
                "type": "Собеседование",
                "title": item.text[:160],
                "context": item.topic or "Без темы",
                "url": f"/interviews/{item.source_id}" if item.source_id else "/interviews",
            }
        )

    # Дедупликация по url+title, сохраняя первый тип.
    seen: set[tuple[str, str]] = set()
    unique = []
    for item in results:
        key = (item["url"], item["title"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return {"query": q, "total": len(unique), "results": unique[:50]}
