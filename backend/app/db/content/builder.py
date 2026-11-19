"""Сборка урока и квиза из компактного описания.

Автор контента заполняет смысловые части, а функция сама раскладывает их
в 14 блоков по методике. Так все уроки имеют одинаковую структуру.
"""

from __future__ import annotations

from typing import Any

Block = tuple[str, dict[str, Any]]
Question = dict[str, Any]


def question(
    kind: str,
    text: str,
    explanation: str,
    options: tuple[tuple[str, bool], ...],
) -> Question:
    if len(options) < 2:
        raise ValueError("У вопроса должно быть не меньше двух вариантов")
    if not any(is_correct for _, is_correct in options):
        raise ValueError("У вопроса должен быть верный вариант")
    return {
        "kind": kind,
        "text": text,
        "explanation": explanation,
        "options": options,
    }


def lesson(
    *,
    title: str,
    summary: str,
    why: str,
    goals: tuple[str, ...],
    concepts: str,
    theory: str,
    visual: Block,
    example: Block,
    application: str,
    mistakes: tuple[str, ...],
    summary_text: str,
    mnemonic: str,
    practice: str,
    questions: tuple[Question, ...],
) -> dict[str, Any]:
    if len(questions) != 10:
        raise ValueError(f"В уроке «{title}» должно быть 10 вопросов")
    return {
        "title": title,
        "summary": summary,
        "why": why,
        "goals": goals,
        "concepts": concepts,
        "theory": theory,
        "visual": visual,
        "example": example,
        "application": application,
        "mistakes": mistakes,
        "summary_text": summary_text,
        "mnemonic": mnemonic,
        "practice": practice,
        "questions": questions,
    }


def build_blocks(data: dict[str, Any]) -> tuple[Block, ...]:
    """14 смысловых частей урока из docs/TEACHING_METHOD.md."""
    return (
        ("heading", {"text": data["title"]}),
        ("callout", {"text": data["why"]}),
        ("list", {"items": list(data["goals"])}),
        ("text", {"text": data["concepts"]}),
        ("text", {"text": data["theory"]}),
        data["visual"],
        data["example"],
        ("callout", {"text": data["application"]}),
        ("list", {"items": list(data["mistakes"])}),
        ("callout", {"text": data["summary_text"]}),
        ("callout", {"text": data["mnemonic"]}),
        ("text", {"text": data["practice"]}),
        (
            "callout",
            {
                "text": (
                    "Квиз из 10 вопросов — под уроком. Он проверяет понимание, "
                    "а не заучивание: ответы можно выбрать один раз, затем видно "
                    "разбор с объяснением."
                )
            },
        ),
        (
            "text",
            {
                "text": (
                    "После отправки квиза разберите каждый неверный ответ. Если результат "
                    "ниже 80 %, вернитесь к краткому конспекту и пройдите квиз повторно."
                )
            },
        ),
    )
