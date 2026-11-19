"""Административное управление программой и просмотр прогресса учеников."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.curriculum_data import COURSE
from app.models import (
    Course,
    Lesson,
    LessonBlock,
    LessonProgress,
    Module,
    Quiz,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
    User,
)
from app.schemas.admin import (
    BlockAdminRead,
    BlocksUpdate,
    CourseAdmin,
    CourseCreate,
    CourseTree,
    CourseUpdate,
    LessonAdminRead,
    LessonBriefAdmin,
    LessonCreate,
    LessonUpdate,
    ModuleAdmin,
    ModuleCreate,
    ModuleProgress,
    ModuleUpdate,
    QuizAdminPayload,
    QuizAdminRead,
    QuizOptionAdmin,
    QuizQuestionAdmin,
    StudentProgress,
    StudentProgressDetail,
)


class AdminNotFoundError(Exception):
    """Объект программы не найден."""


class AdminConflictError(Exception):
    """Позиция или адрес уже заняты."""


class AdminValidationError(Exception):
    """Содержимое квиза или блока некорректно."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise AdminNotFoundError
    return course


def _module(db: Session, module_id: int) -> Module:
    module = db.get(Module, module_id)
    if module is None:
        raise AdminNotFoundError
    return module


def _lesson(db: Session, lesson_id: int) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise AdminNotFoundError
    return lesson


def _counts(db: Session, course_id: int) -> tuple[int, int]:
    modules = int(
        db.scalar(select(func.count()).select_from(Module).where(Module.course_id == course_id))
        or 0
    )
    lessons = int(
        db.scalar(
            select(func.count())
            .select_from(Lesson)
            .join(Module)
            .where(Module.course_id == course_id)
        )
        or 0
    )
    return modules, lessons


def _course_admin(db: Session, course: Course) -> CourseAdmin:
    modules, lessons = _counts(db, course.id)
    return CourseAdmin(
        id=course.id,
        slug=course.slug,
        title=course.title,
        description=course.description,
        is_published=course.is_published,
        module_count=modules,
        lesson_count=lessons,
    )


def list_courses(db: Session) -> list[CourseAdmin]:
    courses = db.scalars(select(Course).order_by(Course.id))
    return [_course_admin(db, course) for course in courses]


def course_tree(db: Session, course_id: int) -> CourseTree:
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.modules).selectinload(Module.lessons).selectinload(Lesson.quiz)
        )
    )
    if course is None:
        raise AdminNotFoundError
    base = _course_admin(db, course)
    modules = [
        ModuleAdmin(
            id=module.id,
            title=module.title,
            summary=module.summary,
            position=module.position,
            lessons=[
                LessonBriefAdmin(
                    id=lesson.id,
                    title=lesson.title,
                    position=lesson.position,
                    estimated_minutes=lesson.estimated_minutes,
                    is_published=lesson.is_published,
                    quiz_id=lesson.quiz.id if lesson.quiz else None,
                )
                for lesson in module.lessons
            ],
        )
        for module in course.modules
    ]
    return CourseTree(**base.model_dump(), modules=modules)


def create_course(db: Session, data: CourseCreate) -> CourseAdmin:
    if db.scalar(select(Course).where(Course.slug == data.slug)) is not None:
        raise AdminConflictError("Курс с таким адресом уже существует")
    course = Course(slug=data.slug, title=data.title, description=data.description)
    db.add(course)
    db.commit()
    db.refresh(course)
    return _course_admin(db, course)


def update_course(db: Session, course_id: int, data: CourseUpdate) -> CourseAdmin:
    course = _course(db, course_id)
    if data.title is not None:
        course.title = data.title
    if "description" in data.model_fields_set:
        course.description = data.description
    if data.is_published is not None:
        course.is_published = data.is_published
    db.commit()
    db.refresh(course)
    return _course_admin(db, course)


def delete_course(db: Session, course_id: int) -> None:
    course = _course(db, course_id)
    db.delete(course)
    db.commit()


def create_module(db: Session, course_id: int, data: ModuleCreate) -> ModuleAdmin:
    course = _course(db, course_id)
    position = (
        int(
            db.scalar(
                select(func.coalesce(func.max(Module.position), 0)).where(
                    Module.course_id == course.id
                )
            )
            or 0
        )
        + 1
    )
    module = Module(
        course_id=course.id,
        title=data.title,
        summary=data.summary,
        position=position,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return ModuleAdmin(
        id=module.id,
        title=module.title,
        summary=module.summary,
        position=module.position,
        lessons=[],
    )


def update_module(db: Session, module_id: int, data: ModuleUpdate) -> ModuleAdmin:
    module = _module(db, module_id)
    if data.position is not None and data.position != module.position:
        taken = db.scalar(
            select(Module.id).where(
                Module.course_id == module.course_id,
                Module.position == data.position,
                Module.id != module.id,
            )
        )
        if taken is not None:
            raise AdminConflictError("Эта позиция модуля уже занята")
        module.position = data.position
    if data.title is not None:
        module.title = data.title
    if "summary" in data.model_fields_set:
        module.summary = data.summary
    db.commit()
    db.refresh(module)
    return ModuleAdmin(
        id=module.id,
        title=module.title,
        summary=module.summary,
        position=module.position,
        lessons=[
            LessonBriefAdmin(
                id=lesson.id,
                title=lesson.title,
                position=lesson.position,
                estimated_minutes=lesson.estimated_minutes,
                is_published=lesson.is_published,
                quiz_id=lesson.quiz.id if lesson.quiz else None,
            )
            for lesson in module.lessons
        ],
    )


def delete_module(db: Session, module_id: int) -> None:
    module = _module(db, module_id)
    db.delete(module)
    db.commit()


def create_lesson(db: Session, module_id: int, data: LessonCreate) -> LessonBriefAdmin:
    module = _module(db, module_id)
    position = (
        int(
            db.scalar(
                select(func.coalesce(func.max(Lesson.position), 0)).where(
                    Lesson.module_id == module.id
                )
            )
            or 0
        )
        + 1
    )
    lesson = Lesson(
        module_id=module.id,
        title=data.title,
        summary=data.summary,
        estimated_minutes=data.estimated_minutes,
        position=position,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return LessonBriefAdmin(
        id=lesson.id,
        title=lesson.title,
        position=lesson.position,
        estimated_minutes=lesson.estimated_minutes,
        is_published=lesson.is_published,
        quiz_id=None,
    )


def lesson_detail(db: Session, lesson_id: int) -> LessonAdminRead:
    lesson = db.scalar(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(selectinload(Lesson.blocks), selectinload(Lesson.quiz))
    )
    if lesson is None:
        raise AdminNotFoundError
    return LessonAdminRead(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        summary=lesson.summary,
        estimated_minutes=lesson.estimated_minutes,
        position=lesson.position,
        is_published=lesson.is_published,
        blocks=[
            BlockAdminRead(type=block.type, content=block.content, position=block.position)
            for block in lesson.blocks
        ],
        quiz_id=lesson.quiz.id if lesson.quiz else None,
    )


def update_lesson(db: Session, lesson_id: int, data: LessonUpdate) -> LessonAdminRead:
    lesson = _lesson(db, lesson_id)
    if data.position is not None and data.position != lesson.position:
        taken = db.scalar(
            select(Lesson.id).where(
                Lesson.module_id == lesson.module_id,
                Lesson.position == data.position,
                Lesson.id != lesson.id,
            )
        )
        if taken is not None:
            raise AdminConflictError("Эта позиция урока уже занята")
        lesson.position = data.position
    if data.title is not None:
        lesson.title = data.title
    if "summary" in data.model_fields_set:
        lesson.summary = data.summary
    if data.estimated_minutes is not None:
        lesson.estimated_minutes = data.estimated_minutes
    if data.is_published is not None:
        lesson.is_published = data.is_published
    db.commit()
    return lesson_detail(db, lesson.id)


def delete_lesson(db: Session, lesson_id: int) -> None:
    lesson = _lesson(db, lesson_id)
    db.delete(lesson)
    db.commit()


def move_lesson(db: Session, lesson_id: int, direction: str) -> LessonAdminRead:
    """Меняет местами урок с соседним по порядку.

    Позиции меняются через временное значение 0: уникальное ограничение
    (module_id, position) не даёт записать две одинаковые позиции.
    """
    lesson = _lesson(db, lesson_id)
    ordered = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.module_id == lesson.module_id)
            .order_by(Lesson.position, Lesson.id)
        )
    )
    index = next((position for position, item in enumerate(ordered) if item.id == lesson.id), None)
    if index is None:
        raise AdminNotFoundError
    target_index = index - 1 if direction == "up" else index + 1
    if target_index < 0 or target_index >= len(ordered):
        raise AdminConflictError("Урок уже стоит на краю списка")
    neighbor = ordered[target_index]
    old_position = lesson.position
    neighbor_position = neighbor.position
    lesson.position = 0
    db.flush()
    neighbor.position = old_position
    db.flush()
    lesson.position = neighbor_position
    db.commit()
    return lesson_detail(db, lesson.id)


def replace_blocks(db: Session, lesson_id: int, data: BlocksUpdate) -> LessonAdminRead:
    lesson = _lesson(db, lesson_id)
    db.execute(delete(LessonBlock).where(LessonBlock.lesson_id == lesson.id))
    for position, block in enumerate(data.blocks, start=1):
        db.add(
            LessonBlock(
                lesson_id=lesson.id,
                type=block.type,
                content=block.content,
                position=position,
            )
        )
    db.commit()
    return lesson_detail(db, lesson.id)


def _quiz_payload(db: Session, quiz: Quiz) -> QuizAdminRead:
    attempts_count = int(
        db.scalar(
            select(func.count()).select_from(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id)
        )
        or 0
    )
    return QuizAdminRead(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        is_published=quiz.is_published,
        attempts_count=attempts_count,
        questions=[
            QuizQuestionAdmin(
                kind=question.kind,
                text=question.text,
                explanation=question.explanation,
                options=[
                    QuizOptionAdmin(text=option.text, is_correct=option.is_correct)
                    for option in question.options
                ],
            )
            for question in quiz.questions
        ],
    )


def get_lesson_quiz(db: Session, lesson_id: int) -> QuizAdminRead | None:
    lesson = db.scalar(
        select(Lesson)
        .where(Lesson.id == lesson_id)
        .options(
            selectinload(Lesson.quiz)
            .selectinload(Quiz.questions)
            .selectinload(QuizQuestion.options)
        )
    )
    if lesson is None:
        raise AdminNotFoundError
    if lesson.quiz is None:
        return None
    return _quiz_payload(db, lesson.quiz)


def replace_lesson_quiz(db: Session, lesson_id: int, data: QuizAdminPayload) -> QuizAdminRead:
    """Создаёт или полностью заменяет квиз урока.

    Замена вопросов удаляет прежние попытки: они ссылаются на старые варианты.
    Интерфейс предупреждает администратора об этом до сохранения.
    """
    lesson = _lesson(db, lesson_id)
    for question in data.questions:
        if not any(option.is_correct for option in question.options):
            raise AdminValidationError("В каждом вопросе должен быть верный вариант")

    existing = db.scalar(select(Quiz).where(Quiz.lesson_id == lesson.id))
    if existing is not None:
        attempts_count = int(
            db.scalar(
                select(func.count())
                .select_from(QuizAttempt)
                .where(QuizAttempt.quiz_id == existing.id)
            )
            or 0
        )
        if attempts_count and not data.confirm_attempts_loss:
            raise AdminConflictError(
                f"У квиза {attempts_count} попыток учеников. Подтвердите удаление истории."
            )
        db.delete(existing)
        db.flush()

    quiz = Quiz(
        lesson_id=lesson.id,
        title=data.title,
        description=data.description,
        is_published=data.is_published,
    )
    db.add(quiz)
    db.flush()
    for question_position, question_data in enumerate(data.questions, start=1):
        question = QuizQuestion(
            quiz_id=quiz.id,
            kind=question_data.kind,
            text=question_data.text,
            explanation=question_data.explanation,
            position=question_position,
        )
        db.add(question)
        db.flush()
        for option_position, option_data in enumerate(question_data.options, start=1):
            db.add(
                QuizOption(
                    question_id=question.id,
                    text=option_data.text,
                    is_correct=option_data.is_correct,
                    position=option_position,
                )
            )
    db.commit()
    return get_lesson_quiz(db, lesson.id)  # type: ignore[return-value]


def delete_lesson_quiz(db: Session, lesson_id: int) -> None:
    lesson = _lesson(db, lesson_id)
    quiz = db.scalar(select(Quiz).where(Quiz.lesson_id == lesson.id))
    if quiz is None:
        raise AdminNotFoundError
    db.delete(quiz)
    db.commit()


def _published_lesson_totals(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Lesson)
            .join(Module)
            .join(Course)
            .where(
                Lesson.is_published.is_(True),
                Course.is_published.is_(True),
                Course.slug == COURSE.slug,
            )
        )
        or 0
    )


def list_students(db: Session) -> list[StudentProgress]:
    total = _published_lesson_totals(db)
    students = list(db.scalars(select(User).where(User.role == "student").order_by(User.email)))

    completed_rows = db.execute(
        select(LessonProgress.user_id, func.count())
        .select_from(LessonProgress)
        .join(Lesson)
        .join(Module)
        .join(Course)
        .where(
            Lesson.is_published.is_(True),
            Course.is_published.is_(True),
            Course.slug == COURSE.slug,
        )
        .group_by(LessonProgress.user_id)
    ).all()
    completed_by_user = {int(user_id): int(count) for user_id, count in completed_rows}

    attempt_rows = db.execute(
        select(
            QuizAttempt.user_id,
            func.count(),
            func.max(QuizAttempt.created_at),
        ).group_by(QuizAttempt.user_id)
    ).all()
    attempts_by_user = {int(user_id): int(count) for user_id, count, _ in attempt_rows}
    last_attempt_by_user = {
        int(user_id): last for user_id, _, last in attempt_rows if last is not None
    }

    last_progress_rows = db.execute(
        select(LessonProgress.user_id, func.max(LessonProgress.completed_at)).group_by(
            LessonProgress.user_id
        )
    ).all()
    last_progress_by_user = {
        int(user_id): last for user_id, last in last_progress_rows if last is not None
    }

    result = []
    for user in students:
        completed = completed_by_user.get(user.id, 0)
        attempts = attempts_by_user.get(user.id, 0)
        last_activity = max(
            [
                value
                for value in (
                    last_attempt_by_user.get(user.id),
                    last_progress_by_user.get(user.id),
                )
                if isinstance(value, datetime)
            ],
            default=None,
        )
        result.append(
            StudentProgress(
                id=user.id,
                email=user.email,
                completed_lessons=completed,
                total_lessons=total,
                percent=(100 * completed // total) if total else 0,
                quiz_attempts=attempts,
                last_activity=last_activity,
            )
        )
    return result


def student_detail(db: Session, user_id: int) -> StudentProgressDetail:
    user = db.get(User, user_id)
    if user is None or user.role != "student":
        raise AdminNotFoundError
    progress = next(item for item in list_students(db) if item.id == user.id)
    modules = db.scalars(
        select(Module)
        .join(Course)
        .where(Course.is_published.is_(True), Course.slug == COURSE.slug)
        .options(selectinload(Module.lessons))
        .order_by(Module.position)
    )
    module_progress = []
    for module in modules:
        published = [lesson for lesson in module.lessons if lesson.is_published]
        completed = (
            int(
                db.scalar(
                    select(func.count())
                    .select_from(LessonProgress)
                    .where(
                        LessonProgress.user_id == user.id,
                        LessonProgress.lesson_id.in_([lesson.id for lesson in published]),
                    )
                )
                or 0
            )
            if published
            else 0
        )
        module_progress.append(
            ModuleProgress(
                module_id=module.id,
                title=module.title,
                completed=completed,
                total=len(published),
            )
        )
    return StudentProgressDetail(**progress.model_dump(), modules=module_progress)
