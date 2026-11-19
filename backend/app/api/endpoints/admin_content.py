"""Административное управление программой, уроками, квизами и учениками."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.admin import (
    BlocksUpdate,
    CourseAdmin,
    CourseCreate,
    CourseTree,
    CourseUpdate,
    LessonAdminRead,
    LessonBriefAdmin,
    LessonCreate,
    LessonMove,
    LessonUpdate,
    ModuleAdmin,
    ModuleCreate,
    ModuleUpdate,
    QuizAdminPayload,
    QuizAdminRead,
    StudentProgress,
    StudentProgressDetail,
)
from app.services import admin_content_service

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Объект программы не найден")


def _conflict(error: admin_content_service.AdminConflictError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def _invalid(error: admin_content_service.AdminValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=error.message)


# --- Курсы -----------------------------------------------------------------------


@router.get("/courses", response_model=list[CourseAdmin], summary="Все курсы")
def list_courses(db: Session = Depends(get_db)) -> list[CourseAdmin]:
    return admin_content_service.list_courses(db)


@router.post("/courses", response_model=CourseAdmin, status_code=201, summary="Создать курс")
def create_course(data: CourseCreate, db: Session = Depends(get_db)) -> CourseAdmin:
    try:
        return admin_content_service.create_course(db, data)
    except admin_content_service.AdminConflictError as error:
        raise _conflict(error) from None


@router.get("/courses/{course_id}", response_model=CourseTree, summary="Дерево курса")
def read_course(course_id: int, db: Session = Depends(get_db)) -> CourseTree:
    try:
        return admin_content_service.course_tree(db, course_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.patch("/courses/{course_id}", response_model=CourseAdmin, summary="Изменить курс")
def update_course(course_id: int, data: CourseUpdate, db: Session = Depends(get_db)) -> CourseAdmin:
    try:
        return admin_content_service.update_course(db, course_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.delete("/courses/{course_id}", status_code=204, summary="Удалить курс")
def delete_course(course_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        admin_content_service.delete_course(db, course_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    return Response(status_code=204)


# --- Модули ----------------------------------------------------------------------


@router.post(
    "/courses/{course_id}/modules",
    response_model=ModuleAdmin,
    status_code=201,
    summary="Создать модуль",
)
def create_module(course_id: int, data: ModuleCreate, db: Session = Depends(get_db)) -> ModuleAdmin:
    try:
        return admin_content_service.create_module(db, course_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.patch("/modules/{module_id}", response_model=ModuleAdmin, summary="Изменить модуль")
def update_module(module_id: int, data: ModuleUpdate, db: Session = Depends(get_db)) -> ModuleAdmin:
    try:
        return admin_content_service.update_module(db, module_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    except admin_content_service.AdminConflictError as error:
        raise _conflict(error) from None


@router.delete("/modules/{module_id}", status_code=204, summary="Удалить модуль")
def delete_module(module_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        admin_content_service.delete_module(db, module_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    return Response(status_code=204)


# --- Уроки -----------------------------------------------------------------------


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonBriefAdmin,
    status_code=201,
    summary="Создать урок",
)
def create_lesson(
    module_id: int, data: LessonCreate, db: Session = Depends(get_db)
) -> LessonBriefAdmin:
    try:
        return admin_content_service.create_lesson(db, module_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.get("/lessons/{lesson_id}", response_model=LessonAdminRead, summary="Урок для редактора")
def read_lesson(lesson_id: int, db: Session = Depends(get_db)) -> LessonAdminRead:
    try:
        return admin_content_service.lesson_detail(db, lesson_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.patch("/lessons/{lesson_id}", response_model=LessonAdminRead, summary="Изменить урок")
def update_lesson(
    lesson_id: int, data: LessonUpdate, db: Session = Depends(get_db)
) -> LessonAdminRead:
    try:
        return admin_content_service.update_lesson(db, lesson_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    except admin_content_service.AdminConflictError as error:
        raise _conflict(error) from None


@router.delete("/lessons/{lesson_id}", status_code=204, summary="Удалить урок")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        admin_content_service.delete_lesson(db, lesson_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    return Response(status_code=204)


@router.post(
    "/lessons/{lesson_id}/move",
    response_model=LessonAdminRead,
    summary="Переставить урок с соседним",
)
def move_lesson(lesson_id: int, data: LessonMove, db: Session = Depends(get_db)) -> LessonAdminRead:
    try:
        return admin_content_service.move_lesson(db, lesson_id, data.direction)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    except admin_content_service.AdminConflictError as error:
        raise _conflict(error) from None


@router.put(
    "/lessons/{lesson_id}/blocks",
    response_model=LessonAdminRead,
    summary="Заменить блоки урока",
)
def replace_blocks(
    lesson_id: int, data: BlocksUpdate, db: Session = Depends(get_db)
) -> LessonAdminRead:
    try:
        return admin_content_service.replace_blocks(db, lesson_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


# --- Квизы -----------------------------------------------------------------------


@router.get(
    "/lessons/{lesson_id}/quiz",
    response_model=QuizAdminRead | None,
    summary="Квиз урока для редактора",
)
def read_quiz(lesson_id: int, db: Session = Depends(get_db)) -> QuizAdminRead | None:
    try:
        return admin_content_service.get_lesson_quiz(db, lesson_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None


@router.put(
    "/lessons/{lesson_id}/quiz",
    response_model=QuizAdminRead,
    summary="Создать или заменить квиз",
)
def replace_quiz(
    lesson_id: int, data: QuizAdminPayload, db: Session = Depends(get_db)
) -> QuizAdminRead:
    try:
        return admin_content_service.replace_lesson_quiz(db, lesson_id, data)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    except admin_content_service.AdminConflictError as error:
        raise _conflict(error) from None
    except admin_content_service.AdminValidationError as error:
        raise _invalid(error) from None


@router.delete("/lessons/{lesson_id}/quiz", status_code=204, summary="Удалить квиз")
def delete_quiz(lesson_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        admin_content_service.delete_lesson_quiz(db, lesson_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
    return Response(status_code=204)


# --- Ученики ---------------------------------------------------------------------


@router.get("/students", response_model=list[StudentProgress], summary="Прогресс учеников")
def list_students(db: Session = Depends(get_db)) -> list[StudentProgress]:
    return admin_content_service.list_students(db)


@router.get(
    "/students/{user_id}",
    response_model=StudentProgressDetail,
    summary="Прогресс ученика по модулям",
)
def read_student(user_id: int, db: Session = Depends(get_db)) -> StudentProgressDetail:
    try:
        return admin_content_service.student_detail(db, user_id)
    except admin_content_service.AdminNotFoundError:
        raise _not_found() from None
