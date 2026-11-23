"""Публичный раздел разборов собеседований: файлы и вопросы с ответами."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    InterviewQuestion,
    InterviewQuestionSource,
    InterviewSource,
)

router = APIRouter(prefix="/interviews", tags=["Собеседования"])

# Публичный раздел: все approved-ответы, но с честной категорией.
# Промпт и учебные PDF не выдаём за реальные собеседования.
CATEGORY_BY_ID = {
    13: "course",
    14: "course",
    15: "prompt",
    17: "method",
    18: "method",
    19: "method",
    21: "template",
    22: "template",
    23: "template",
    24: "template",
}
DISPLAY_NAMES = {
    6: "Собеседование: Сбер",
    13: "Учебный курс: Тестирование",
    14: "Учебный курс: Тестирование (часть 2)",
    15: "Промпт: план обучения",
    17: "Методика и профиль нагрузочного тестирования",
    18: "Цели, события и показатели НТ",
    19: "Презентация к уроку",
    21: "Шаблон: МНТ",
    22: "Шаблон: мини-отчёт по НТ",
    23: "Шаблон: отчёт по результатам НТ",
    24: "Шаблон: экспресс-отчёт",
}


def _display_name(source: InterviewSource) -> str:
    return DISPLAY_NAMES.get(source.id, source.filename)


def _category(source: InterviewSource) -> str:
    return CATEGORY_BY_ID.get(source.id, "interview")


@router.get("/sources", summary="Файлы собеседований с разборами")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    counts = dict(
        db.execute(
            select(
                InterviewQuestionSource.source_id,
                func.count(func.distinct(InterviewQuestionSource.question_id)),
            )
            .join(InterviewQuestion, InterviewQuestion.id == InterviewQuestionSource.question_id)
            .where(InterviewQuestion.status == "approved")
            .group_by(InterviewQuestionSource.source_id)
        ).all()
    )
    sources = db.scalars(select(InterviewSource).order_by(InterviewSource.filename)).all()
    return [
        {
            "id": source.id,
            "filename": _display_name(source),
            "category": _category(source),
            "questions_count": counts.get(source.id, 0),
            "created_at": source.created_at,
        }
        for source in sources
        if counts.get(source.id, 0) > 0
    ]


@router.get("/sources/{source_id}", summary="Вопросы и ответы из файла")
def read_source(source_id: int, db: Session = Depends(get_db)) -> dict:
    source = db.get(InterviewSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    questions = db.scalars(
        select(InterviewQuestion)
        .join(InterviewQuestionSource, InterviewQuestionSource.question_id == InterviewQuestion.id)
        .where(
            InterviewQuestionSource.source_id == source_id,
            InterviewQuestion.status == "approved",
        )
        .order_by(InterviewQuestion.topic, InterviewQuestion.id)
    ).all()
    if not questions:
        raise HTTPException(status_code=404, detail="Вопросы не найдены")
    return {
        "id": source.id,
        "filename": _display_name(source),
        "category": _category(source),
        "questions_count": len(questions),
        "questions": [
            {
                "id": item.id,
                "text": item.text,
                "topic": item.topic,
                "difficulty": item.difficulty,
                "level": item.level,
                "reference_answer": item.reference_answer,
                "answer_criteria": item.answer_criteria,
            }
            for item in questions
        ],
    }
