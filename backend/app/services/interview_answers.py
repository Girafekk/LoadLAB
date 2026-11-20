"""Генерация эталонных ответов для банка вопросов."""

from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewQuestion
from app.services import ai_teacher_service


def generate_answers(
    db: Session,
    limit: int | None = None,
    batch_size: int = 10,
    ids: list[int] | None = None,
) -> dict[str, int]:
    query = (
        select(InterviewQuestion)
        .where(InterviewQuestion.reference_answer.is_(None))
        .order_by(InterviewQuestion.id)
    )
    if ids:
        query = query.where(InterviewQuestion.id.in_(ids))
    if limit:
        query = query.limit(limit)
    questions = list(db.scalars(query))
    generated = 0
    failed = 0
    system = (
        "Ты Senior Load Tester и интервьюер. Для каждого вопроса дай эталонный "
        "ответ для Junior-кандидата и 3 критерия оценки. Верни только JSON-массив "
        'без Markdown: [{"id": число, "answer": "3–5 предложений", '
        '"criteria": ["...", "...", "..."]}]. Без персональных данных.'
    )
    for start in range(0, len(questions), batch_size):
        chunk = questions[start : start + batch_size]
        payload = [
            {"id": item.id, "question": item.text, "topic": item.topic or ""} for item in chunk
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
        for question in chunk:
            item = parsed.get(question.id)
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
            question.reference_answer = answer.replace("\x00", "")[:4_000]
            question.answer_criteria = criteria_text.replace("\x00", "")[:2_000]
            generated += 1
        db.commit()
    return {"generated": generated, "fallback": failed, "total": len(questions)}
