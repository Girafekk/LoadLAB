"""Полный аудит файлов собеседований против банка и курса.

Запуск внутри backend-контейнера:
    python tools/audit_interview_sources.py /tmp/interview_materials /tmp/audit.md
"""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select

from app.db.session import Session, get_engine
from app.models import InterviewQuestion, QuizQuestion
from app.services.interview_service import _extract_text

SUFFIXES = {".txt", ".pdf", ".doc", ".docx"}
THRESHOLD = 0.72


def normalize(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def similar(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def question_lines(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = " ".join(raw.split())
        line = re.sub(r"^[\d\-–—.)\s]+", "", line).strip()
        if "?" not in line or len(line) < 15:
            continue
        cut = line.find("?")
        candidate = line[: cut + 1].strip()
        if len(candidate) >= 15:
            found.append((number, candidate))
    return found


def main() -> int:
    source_dir = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    db = Session(get_engine())
    bank = [
        (item.id, item.text, normalize(item.text)) for item in db.scalars(select(InterviewQuestion))
    ]
    course = [
        (item.id, item.text, normalize(item.text)) for item in db.scalars(select(QuizQuestion))
    ]
    rows: list[dict[str, object]] = []

    for path in sorted(source_dir.iterdir()):
        if path.suffix.lower() not in SUFFIXES:
            continue
        try:
            text = _extract_text(path, path.suffix.lower())
        except Exception as error:  # noqa: BLE001 — отчёт должен показать сбой
            rows.append({"file": path.name, "line": 0, "question": f"ОШИБКА: {error}"})
            continue
        for number, question in question_lines(text):
            normalized = normalize(question)
            bank_match = max(
                ((similar(normalized, item[2]), item) for item in bank),
                default=(0.0, None),
            )
            course_match = max(
                ((similar(normalized, item[2]), item) for item in course),
                default=(0.0, None),
            )
            best = max(bank_match[0], course_match[0])
            if best < THRESHOLD:
                rows.append(
                    {
                        "file": path.name,
                        "line": number,
                        "question": question,
                        "bank_score": round(bank_match[0], 2),
                        "course_score": round(course_match[0], 2),
                    }
                )

    report_path.write_text(
        "# Полный аудит строк-вопросов\n\n"
        f"Порог совпадения: {THRESHOLD}. Файлов: {len(list(source_dir.iterdir()))}.\n\n"
        f"Не найдено в банке/курсе: **{len(rows)}** строк.\n\n"
        + "\n".join(f"- `{row['file']}:{row['line']}` — {row['question']}" for row in rows[:500]),
        encoding="utf-8",
    )
    print(json.dumps({"uncovered": len(rows), "report": str(report_path)}, ensure_ascii=False))
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
