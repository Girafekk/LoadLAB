"""Загрузка учебного контента 8 недель в базу.

Структура курса создаётся `seed_curriculum`; этот модуль наполняет уроки
блоками и квизами и публикует программу. Повторный запуск не перезаписывает
уже созданный контент, если не указан `--refresh`.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.content import WEEKS
from app.db.content.builder import build_blocks
from app.db.curriculum_data import COURSE
from app.db.seed import seed_curriculum
from app.db.session import get_engine
from app.models import Course, Lesson, LessonBlock, Quiz, QuizOption, QuizQuestion


@dataclass(frozen=True)
class ContentResult:
    lessons_filled: int
    quizzes_created: int


def _create_quiz(session: Session, lesson: Lesson, data: dict) -> Quiz:
    quiz = Quiz(
        lesson_id=lesson.id,
        title=f"Проверка: {lesson.title}",
        description="10 вопросов с объяснением каждого ответа.",
        is_published=True,
    )
    session.add(quiz)
    session.flush()
    for position, question_data in enumerate(data["questions"], start=1):
        question = QuizQuestion(
            quiz_id=quiz.id,
            kind=question_data["kind"],
            text=question_data["text"],
            explanation=question_data["explanation"],
            position=position,
        )
        session.add(question)
        session.flush()
        for option_position, (text, is_correct) in enumerate(question_data["options"], start=1):
            session.add(
                QuizOption(
                    question_id=question.id,
                    text=text,
                    is_correct=is_correct,
                    position=option_position,
                )
            )
    session.flush()
    return quiz


def seed_content(
    session: Session, *, refresh: bool = False, confirm_refresh: bool = False
) -> ContentResult:
    """Наполняет курс контентом и публикует его. Без commit."""
    if refresh and not confirm_refresh:
        raise RuntimeError(
            "--refresh удаляет попытки всех квизов. Добавьте --confirm, "
            "если это действительно нужно."
        )
    course = session.scalar(select(Course).where(Course.slug == COURSE.slug))
    if course is None:
        raise RuntimeError("Сначала загрузите структуру курса: python -m app.db.seed")

    lessons_filled = 0
    quizzes_created = 0
    course.is_published = True

    for module in course.modules:
        week = WEEKS.get(module.position)
        if week is None:
            raise RuntimeError(f"Нет контента для модуля {module.position}")
        if len(week) != len(module.lessons):
            raise RuntimeError(
                f"Модуль {module.position}: уроков в программе {len(module.lessons)}, "
                f"контента {len(week)}"
            )

        for lesson, data in zip(module.lessons, week, strict=True):
            lesson.title = data["title"]
            lesson.summary = data["summary"]
            lesson.is_published = True

            if refresh and lesson.blocks:
                session.execute(delete(LessonBlock).where(LessonBlock.lesson_id == lesson.id))
                session.expire(lesson, ["blocks"])
            if not lesson.blocks:
                for position, (block_type, content) in enumerate(build_blocks(data), start=1):
                    session.add(
                        LessonBlock(
                            lesson_id=lesson.id,
                            type=block_type,
                            content=content,
                            position=position,
                        )
                    )
                lessons_filled += 1

            quiz = session.scalar(select(Quiz).where(Quiz.lesson_id == lesson.id))
            if refresh and quiz is not None:
                session.delete(quiz)
                session.flush()
                quiz = None
            if quiz is None:
                _create_quiz(session, lesson, data)
                quizzes_created += 1
            else:
                quiz.is_published = True

    session.flush()
    return ContentResult(lessons_filled=lessons_filled, quizzes_created=quizzes_created)


def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузка учебного контента 8 недель.")
    parser.add_argument(
        "--refresh", action="store_true", help="пересоздать блоки и квизы (попытки удаляются)"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="подтвердить удаление попыток при --refresh",
    )
    args = parser.parse_args()

    if args.refresh and os.environ.get("ENVIRONMENT") == "production":
        parser.error("--refresh запрещён в production")
    if args.refresh and not args.confirm:
        parser.error("--refresh удаляет попытки; добавьте --confirm")

    with Session(get_engine()) as session:
        seed_curriculum(session)
        result = seed_content(session, refresh=args.refresh, confirm_refresh=args.confirm)
        session.commit()

    print(f"Заполнено уроков: {result.lessons_filled}, создано квизов: {result.quizzes_created}.")


if __name__ == "__main__":
    main()
