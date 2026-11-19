"""Начальные данные: структура основного курса.

Запуск (из папки backend):

    python -m app.db.seed

Сид идемпотентный: его можно запускать сколько угодно раз. Он создаёт только
то, чего ещё нет в базе, и не меняет и не удаляет существующие строки.
"""

import argparse
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.curriculum_data import COURSE, CourseData
from app.db.demo_lesson import publish_demo_lesson
from app.db.demo_quiz import publish_demo_quiz
from app.db.session import get_engine
from app.models import Course, Lesson, LessonBlock, Module, Quiz


@dataclass(frozen=True)
class SeedResult:
    """Сколько строк создано этим запуском (0 — значит, всё уже было)."""

    courses_created: int
    modules_created: int
    lessons_created: int


def seed_curriculum(session: Session, data: CourseData = COURSE) -> SeedResult:
    """Создаёт курс, модули и уроки, которых ещё нет в базе.

    Курс ищется по `slug`, модуль — по номеру внутри курса, урок — по номеру
    внутри модуля. Уроки создаются без блоков: контент появится позже.
    Функция не делает commit — это решает вызывающий код.
    """
    courses_created = modules_created = lessons_created = 0

    course = session.scalar(select(Course).where(Course.slug == data.slug))
    if course is None:
        course = Course(
            slug=data.slug,
            title=data.title,
            description=data.description,
            is_published=False,
        )
        session.add(course)
        session.flush()
        courses_created += 1

    for module_position, module_data in enumerate(data.modules, start=1):
        module = session.scalar(
            select(Module).where(Module.course_id == course.id, Module.position == module_position)
        )
        if module is None:
            module = Module(
                course_id=course.id,
                title=module_data.title,
                summary=module_data.summary,
                position=module_position,
            )
            session.add(module)
            session.flush()
            modules_created += 1

        for lesson_position, lesson_title in enumerate(module_data.lessons, start=1):
            content_key = f"w{module_position}-l{lesson_position}"
            # Сначала ищем по неизменяемому ключу: перестановка урока не должна
            # приводить к созданию дубля или конфликту уникального ключа.
            if (
                session.scalar(
                    select(Lesson).where(
                        Lesson.module_id == module.id, Lesson.content_key == content_key
                    )
                )
                is not None
            ):
                continue
            # Старый урок без ключа можно привязать только по названию.
            legacy = session.scalar(
                select(Lesson).where(
                    Lesson.module_id == module.id,
                    Lesson.title == lesson_title,
                    Lesson.content_key.is_(None),
                )
            )
            if legacy is not None:
                legacy.content_key = content_key
                continue
            if (
                session.scalar(
                    select(Lesson).where(
                        Lesson.module_id == module.id, Lesson.title == lesson_title
                    )
                )
                is not None
            ):
                # Урок с таким названием уже есть, но с другим ключом:
                # не создаём второй и не перезаписываем чужую привязку.
                continue
            session.add(
                Lesson(
                    module_id=module.id,
                    title=lesson_title,
                    position=lesson_position,
                    content_key=content_key,
                )
            )
            lessons_created += 1

    session.flush()
    return SeedResult(courses_created, modules_created, lessons_created)


def clear_demo_content(session: Session) -> None:
    """Удаляет блоки демо-урока и демо-квиз вместе с попытками.

    Нужно только для обновления демонстрационного контента при разработке:
    обычный сид никогда не меняет существующие строки. Попытки квиза при этом
    удаляются, поэтому команда не предназначена для рабочих баз.
    """
    lesson = session.scalar(
        select(Lesson)
        .join(Module)
        .join(Course)
        .where(
            Course.slug == COURSE.slug,
            Module.position == 1,
            Lesson.position == 1,
        )
    )
    if lesson is None:
        return
    session.execute(delete(LessonBlock).where(LessonBlock.lesson_id == lesson.id))
    session.execute(delete(Quiz).where(Quiz.lesson_id == lesson.id))
    session.flush()


def demo_publication_state(session: Session) -> tuple[bool, bool] | None:
    """Запоминает, были ли курс и демо-урок опубликованы до обновления контента."""
    course = session.scalar(select(Course).where(Course.slug == COURSE.slug))
    if course is None:
        return None
    lesson = session.scalar(
        select(Lesson)
        .join(Module)
        .where(Module.course_id == course.id, Module.position == 1, Lesson.position == 1)
    )
    if lesson is None:
        return None
    return course.is_published, lesson.is_published


def restore_demo_publication(session: Session, state: tuple[bool, bool]) -> None:
    """Возвращает прежние флаги публикации после пересоздания контента.

    Обычный сид публикует демо-урок только при первом наполнении. Команда
    `--refresh-demo` не должна заново открывать то, что администратор скрыл.
    """
    course = session.scalar(select(Course).where(Course.slug == COURSE.slug))
    if course is None:
        return
    lesson = session.scalar(
        select(Lesson)
        .join(Module)
        .where(Module.course_id == course.id, Module.position == 1, Lesson.position == 1)
    )
    course.is_published = state[0]
    if lesson is not None:
        lesson.is_published = state[1]


def demo_quiz_publication_state(session: Session) -> bool | None:
    """Был ли демо-квиз опубликован до пересоздания (None — квиза не было)."""
    course = session.scalar(select(Course).where(Course.slug == COURSE.slug))
    if course is None:
        return None
    lesson = session.scalar(
        select(Lesson)
        .join(Module)
        .where(Module.course_id == course.id, Module.position == 1, Lesson.position == 1)
    )
    if lesson is None:
        return None
    quiz = session.scalar(select(Quiz).where(Quiz.lesson_id == lesson.id))
    return None if quiz is None else quiz.is_published


def restore_quiz_publication(session: Session, was_published: bool | None) -> None:
    """Возвращает прежний флаг публикации демо-квиза после пересоздания."""
    if was_published is None:
        return
    course = session.scalar(select(Course).where(Course.slug == COURSE.slug))
    if course is None:
        return
    lesson = session.scalar(
        select(Lesson)
        .join(Module)
        .where(Module.course_id == course.id, Module.position == 1, Lesson.position == 1)
    )
    if lesson is None:
        return
    quiz = session.scalar(select(Quiz).where(Quiz.lesson_id == lesson.id))
    if quiz is not None:
        quiz.is_published = was_published


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Загрузка структуры курса и демонстрационных материалов."
    )
    parser.add_argument(
        "--refresh-demo",
        action="store_true",
        help="пересоздать блоки демо-урока и демо-квиз (попытки квиза удаляются)",
    )
    args = parser.parse_args()

    if args.refresh_demo and get_settings().is_production:
        parser.error("--refresh-demo удаляет попытки и запрещён в production")

    with Session(get_engine()) as session:
        result = seed_curriculum(session)
        publication_state = demo_publication_state(session) if args.refresh_demo else None
        quiz_publication_state = demo_quiz_publication_state(session) if args.refresh_demo else None
        if args.refresh_demo:
            clear_demo_content(session)
        blocks_created = publish_demo_lesson(session)
        quiz_questions_created = publish_demo_quiz(session)
        if publication_state is not None:
            restore_demo_publication(session, publication_state)
        if quiz_publication_state is not None:
            restore_quiz_publication(session, quiz_publication_state)
        session.commit()

        course_id = session.scalar(select(Course.id).where(Course.slug == COURSE.slug))
        modules_total = len(
            session.scalars(select(Module.id).where(Module.course_id == course_id)).all()
        )
        lessons_total = len(
            session.scalars(
                select(Lesson.id).join(Module).where(Module.course_id == course_id)
            ).all()
        )

    print(
        f"Создано: курсов — {result.courses_created}, "
        f"модулей — {result.modules_created}, уроков — {result.lessons_created}."
    )
    print(f"Всего в курсе «{COURSE.title}»: модулей — {modules_total}, уроков — {lessons_total}.")
    print(f"Демонстрационный урок опубликован, создано блоков — {blocks_created}.")
    print(f"Демонстрационный квиз опубликован, создано вопросов — {quiz_questions_created}.")


if __name__ == "__main__":
    main()
