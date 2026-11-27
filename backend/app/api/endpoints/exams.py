"""Модульные контрольные и итоговый экзамен."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Lesson, Module, Quiz, QuizQuestion

router = APIRouter(prefix="/exams", tags=["Экзамены"])


class ExamAnswer(BaseModel):
    question_id: int
    option_ids: list[int] = Field(default_factory=list)


class ExamSubmit(BaseModel):
    answers: list[ExamAnswer]


@router.get("/modules", summary="Модули для контрольных")
def modules(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Module.id, Module.title, Module.position, func.count(QuizQuestion.id))
        .join(Lesson, Lesson.module_id == Module.id)
        .join(Quiz, Quiz.lesson_id == Lesson.id)
        .join(QuizQuestion, QuizQuestion.quiz_id == Quiz.id)
        .group_by(Module.id, Module.title, Module.position)
        .order_by(Module.position)
    ).all()
    return [
        {"id": module_id, "title": title, "position": position, "questions": count}
        for module_id, title, position, count in rows
    ]


@router.get("/questions", summary="Вопросы для экзамена")
def questions(
    module_id: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
) -> dict:
    query = (
        select(QuizQuestion)
        .join(Quiz, Quiz.id == QuizQuestion.quiz_id)
        .join(Lesson, Lesson.id == Quiz.lesson_id)
        .options(selectinload(QuizQuestion.options))
    )
    if module_id:
        query = query.where(Lesson.module_id == module_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(func.random()).limit(limit)).all()
    return {
        "total": total,
        "questions": [
            {
                "id": item.id,
                "text": item.text,
                "options": [
                    {"id": option.id, "text": option.text}
                    for option in sorted(item.options, key=lambda option: option.position)
                ],
            }
            for item in items
        ],
    }


@router.post("/submit", summary="Проверить экзамен")
def submit(data: ExamSubmit, db: Session = Depends(get_db)) -> dict:
    if not data.answers:
        raise HTTPException(status_code=422, detail="Нет ответов")
    ids = [answer.question_id for answer in data.answers]
    items = db.scalars(
        select(QuizQuestion)
        .where(QuizQuestion.id.in_(ids))
        .options(selectinload(QuizQuestion.options))
    ).all()
    by_id = {item.id: item for item in items}
    details = []
    correct_count = 0
    for answer in data.answers:
        item = by_id.get(answer.question_id)
        if item is None:
            continue
        correct = {option.id for option in item.options if option.is_correct}
        chosen = set(answer.option_ids)
        is_correct = chosen == correct
        correct_count += int(is_correct)
        details.append(
            {
                "question_id": item.id,
                "correct": is_correct,
                "correct_option_ids": sorted(correct),
                "explanation": item.explanation,
            }
        )
    return {
        "total": len(details),
        "correct": correct_count,
        "percent": round(correct_count * 100 / len(details)) if details else 0,
        "details": details,
    }
