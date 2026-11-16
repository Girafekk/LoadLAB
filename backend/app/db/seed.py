"""Начальные данные: структура основного курса.

Запуск (из папки backend):

    python -m app.db.seed

Сид идемпотентный: его можно запускать сколько угодно раз. Он создаёт только
то, чего ещё нет в базе, и не меняет и не удаляет существующие строки.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.curriculum_data import COURSE, CourseData
from app.db.session import get_engine
from app.models import Course, Lesson, Module


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

        existing_positions = set(
            session.scalars(select(Lesson.position).where(Lesson.module_id == module.id))
        )
        for lesson_position, lesson_title in enumerate(module_data.lessons, start=1):
            if lesson_position in existing_positions:
                continue
            session.add(Lesson(module_id=module.id, title=lesson_title, position=lesson_position))
            lessons_created += 1

    session.flush()
    return SeedResult(courses_created, modules_created, lessons_created)


def main() -> None:
    with Session(get_engine()) as session:
        result = seed_curriculum(session)
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


if __name__ == "__main__":
    main()
