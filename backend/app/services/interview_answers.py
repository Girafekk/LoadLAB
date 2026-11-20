"""Генерация эталонных ответов для банка вопросов."""

from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import InterviewQuestion
from app.services import ai_teacher_service


def generate_answers(
    db: Session,
    limit: int | None = None,
    batch_size: int = 10,
    ids: list[int] | None = None,
    force: bool = False,
    allow_external: bool = False,
) -> dict[str, int]:
    query = select(InterviewQuestion).order_by(InterviewQuestion.id)
    if not force:
        query = query.where(InterviewQuestion.reference_answer.is_(None))
    if ids:
        query = query.where(InterviewQuestion.id.in_(ids))
    if limit:
        query = query.limit(limit)
    questions = list(db.scalars(query))
    records = [(item.id, item.text, item.topic or "") for item in questions]
    if not allow_external:
        return {"generated": 0, "fallback": len(records), "total": len(records)}
    bind = db.get_bind()
    separate = isinstance(bind, Engine)
    if separate:
        db.close()
    generated = 0
    failed = 0
    system = (
        "Ты Senior Load Tester и интервьюер. Пиши для начинающего специалиста "
        "простым русским языком, как для 10 класса. Каждый ответ строго по шаблону: "
        '"Коротко: <смысл в 1–2 предложениях>. Пример: <пример из теста>. '
        'Граница: <чего не проверяли или когда не работает>." '
        "Все предложения короче 20 слов. Каждый термин расшифруй при первом "
        "упоминании. Не используй слово «просто». Ответ должен быть точным и "
        "достаточным для Junior-собеседования. Верни только JSON-массив без "
        'Markdown: [{"id": число, "answer": "текст по шаблону", '
        '"criteria": ["...", "...", "..."]}]. Без персональных данных.'
    )
    for start in range(0, len(records), batch_size):
        chunk = records[start : start + batch_size]
        payload = [
            {"id": question_id, "question": question_text, "topic": topic}
            for question_id, question_text, topic in chunk
        ]
        raw = ai_teacher_service.complete_external(
            system,
            "Вопросы:\n" + json.dumps(payload, ensure_ascii=False),
            timeout=60,
        )
        parsed: dict[int, dict[str, object]] = {}
        if raw:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and isinstance(item.get("id"), int):
                                parsed[item["id"]] = item
                except json.JSONDecodeError:
                    parsed = {}
        work = Session(bind=bind) if separate else db
        try:
            for question_id, _question_text, _topic in chunk:
                item = parsed.get(question_id)
                answer = str(item.get("answer", "")).strip() if item else ""
                criteria = item.get("criteria") if item else None
                if criteria is not None and not isinstance(criteria, list):
                    criteria = None
                criteria_text = (
                    "\n".join(f"- {str(value).strip()}" for value in criteria if str(value).strip())
                    if criteria
                    else ""
                )
                if not answer:
                    failed += 1
                    continue
                question = work.get(InterviewQuestion, question_id)
                if question is None:
                    failed += 1
                    continue
                question.reference_answer = answer.replace("\x00", "")[:4_000]
                question.answer_criteria = criteria_text.replace("\x00", "")[:2_000]
                generated += 1
            work.commit()
        finally:
            if separate:
                work.close()
    return {"generated": generated, "fallback": failed, "total": len(records)}
