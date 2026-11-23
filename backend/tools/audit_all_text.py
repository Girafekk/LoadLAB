"""Аудит всех строк файлов собеседований, не только вопросов."""

from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select

from app.db.session import Session, get_engine
from app.models import InterviewQuestion, Lesson, QuizQuestion
from app.services.interview_service import _extract_text

SUFFIXES = {".txt", ".pdf", ".doc", ".docx"}
QUESTION_WORDS = (
    "что ",
    "как ",
    "зачем",
    "почему",
    "какой",
    "какая",
    "какие",
    "где ",
    "когда",
    "сколько",
    "чем ",
    "кто ",
    "расскажи",
    "объясни",
    "опиши",
    "приведи",
    "сравни",
    "назови",
    "можешь",
    "можно ли",
    "есть ли",
)


def normalize(value: str) -> str:
    value = value.casefold().replace("ё", "е")
    value = re.sub(r"[^a-zа-я0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def similar(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def looks_question(line: str) -> bool:
    lowered = line.casefold().strip()
    return "?" in line or lowered.startswith(QUESTION_WORDS)


def main() -> int:
    source_dir = Path(sys.argv[1])
    report = Path(sys.argv[2])
    db = Session(get_engine())
    bank = [(item.id, normalize(item.text)) for item in db.scalars(select(InterviewQuestion))]
    course = [(item.id, normalize(item.text)) for item in db.scalars(select(QuizQuestion))]
    lesson_titles = [normalize(title) for title in db.scalars(select(Lesson.title))]
    rows = []
    counters = {
        "files": 0,
        "lines": 0,
        "questions": 0,
        "statements": 0,
        "uncovered_questions": 0,
        "uncovered_statements": 0,
    }

    for path in sorted(source_dir.iterdir()):
        if path.suffix.lower() not in SUFFIXES:
            continue
        counters["files"] += 1
        try:
            text = _extract_text(path, path.suffix.lower())
        except Exception as error:  # noqa: BLE001
            rows.append({"file": path.name, "line": 0, "kind": "error", "text": str(error)})
            continue
        for number, raw in enumerate(text.splitlines(), start=1):
            line = " ".join(raw.split())
            if len(line) < 10:
                continue
            counters["lines"] += 1
            normalized = normalize(line)
            is_question = looks_question(line)
            counters["questions" if is_question else "statements"] += 1
            best_question = max(
                (similar(normalized, value) for _, value in bank + course),
                default=0.0,
            )
            best_title = max((similar(normalized, value) for value in lesson_titles), default=0.0)
            if is_question:
                covered = best_question >= 0.62 or best_title >= 0.55
                if not covered:
                    counters["uncovered_questions"] += 1
                    rows.append(
                        {
                            "file": path.name,
                            "line": number,
                            "kind": "question",
                            "text": line[:500],
                            "score": round(best_question, 2),
                        }
                    )
            else:
                # Для утверждений проверяем, есть ли пересечение по словам с курсом.
                words = {word for word in normalized.split() if len(word) >= 5}
                course_words = set(" ".join(value for _, value in course).split())
                overlap = len(words & course_words)
                if words and overlap == 0:
                    counters["uncovered_statements"] += 1
                    rows.append(
                        {
                            "file": path.name,
                            "line": number,
                            "kind": "statement",
                            "text": line[:500],
                            "score": 0,
                        }
                    )

    lines = [
        "# Аудит всех строк файлов",
        "",
        json.dumps(counters, ensure_ascii=False, indent=2),
        "",
        f"Строк для проверки: {len(rows)}.",
        "",
    ]
    lines.extend(f"- `{row['file']}:{row['line']}` [{row['kind']}] — {row['text']}" for row in rows)
    report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(counters, ensure_ascii=False))
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
