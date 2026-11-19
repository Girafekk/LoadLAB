"""Логика учебных тренажёров: HTTP, SQL, Linux и анализ результатов."""

from __future__ import annotations

import re
import shlex
import sqlite3
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Lesson, Module
from app.schemas.trainers import (
    AnalysisExercise,
    AnalysisResult,
    CheckResult,
    HttpExercise,
    LinuxExercise,
    LinuxResult,
    SqlExercise,
    SqlResult,
)

HTTP_EXERCISES = (
    {
        "id": "http-list",
        "title": "Список товаров",
        "task": "Запросите список товаров учебного магазина.",
        "method": "GET",
        "path": "/api/products",
        "hint": "Метод GET, путь без параметров.",
    },
    {
        "id": "http-search",
        "title": "Поиск товара",
        "task": "Найдите товары со словом «монитор» через параметр q.",
        "method": "GET",
        "path": "/api/products?q=монитор",
        "hint": "Параметр передаётся после вопросительного знака.",
    },
    {
        "id": "http-login",
        "title": "Вход",
        "task": "Отправьте POST на вход с JSON-телом.",
        "method": "POST",
        "path": "/api/login",
        "hint": "Метод POST, путь /api/login.",
    },
    {
        "id": "http-cart",
        "title": "Добавить в корзину",
        "task": "Добавьте товар 1 в корзину методом POST.",
        "method": "POST",
        "path": "/api/cart/items",
        "hint": "Путь /api/cart/items, товар передаётся в теле.",
    },
)

SQL_EXERCISES = (
    {
        "id": "sql-course",
        "title": "Название курса",
        "task": "Выведите title курса с slug = 'load-testing'.",
        "hint": "SELECT title FROM courses WHERE slug = 'load-testing'",
        "expected": "Нагрузочное тестирование с нуля",
    },
    {
        "id": "sql-modules",
        "title": "Число модулей",
        "task": "Посчитайте модули курса load-testing.",
        "hint": "COUNT(*) и подзапрос по courses.slug.",
        "expected": "8",
    },
    {
        "id": "sql-published",
        "title": "Первый опубликованный урок",
        "task": "Выведите title первого опубликованного урока по id.",
        "hint": "WHERE is_published = true ORDER BY id LIMIT 1",
        "expected": "Как делают программы: команда, роли, место тестировщика",
    },
)

LINUX_EXERCISES = (
    {
        "id": "linux-pwd",
        "title": "Где я",
        "task": "Выведите текущую папку /srv/app.",
        "hint": "pwd",
        "command": "pwd",
        "expected": "/srv/app",
    },
    {
        "id": "linux-grep",
        "title": "Ошибки в логе",
        "task": "Найдите строки ERROR в /srv/app/app.log.",
        "hint": "grep ERROR /srv/app/app.log",
        "command": "grep",
        "expected": "ERROR",
    },
    {
        "id": "linux-tail",
        "title": "Последние строки",
        "task": "Покажите последние 2 строки /srv/app/app.log.",
        "hint": "tail -n 2 /srv/app/app.log",
        "command": "tail",
        "expected": "ready",
        "expected_lines": 2,
    },
)

ANALYSIS = (
    {
        "id": "an-rps",
        "title": "RPS и ошибки",
        "situation": (
            "За 60 секунд прошло 12 000 запросов, 600 из них с ошибкой 500. "
            "RPS = 200. Что важно добавить в вывод?"
        ),
        "options": [
            "Что 5 % запросов закончились ошибкой",
            "Что RPS всегда равен числу пользователей",
            "Что ошибки можно не учитывать",
            "Что время ответа не важно",
        ],
        "correct": 0,
        "feedback": "RPS не отменяет ошибки: 600 / 12 000 = 5 %.",
    },
    {
        "id": "an-p95",
        "title": "Среднее и p95",
        "situation": "Среднее 300 мс, p95 1200 мс. Что это значит?",
        "options": [
            "Все запросы длились 1200 мс",
            "У части запросов время заметно выше среднего",
            "p95 не может быть больше среднего",
            "Ошибок ровно 5 %",
        ],
        "correct": 1,
        "feedback": "p95 показывает медленный хвост, который среднее сглаживает.",
    },
    {
        "id": "an-saturation",
        "title": "Точка насыщения",
        "situation": (
            "При росте с 100 до 140 пользователей RPS почти не вырос, p95 вырос "
            "с 0,5 до 6 секунд, ошибки выросли до 8 %. Что произошло?"
        ),
        "options": [
            "Система стала быстрее",
            "Данные нельзя сравнивать",
            "Система подошла к пределу производительности",
            "Нужно просто добавить данных в CSV",
        ],
        "correct": 2,
        "feedback": "RPS упёрся, задержка и ошибки выросли — признак насыщения.",
    },
)

FILES: dict[str, str] = {
    "/srv/app/app.log": (
        "INFO start\n"
        "INFO connected to db\n"
        "ERROR timeout while calling catalog\n"
        "WARN retry 1\n"
        "ERROR timeout while calling catalog\n"
        "INFO ready\n"
        "INFO ready\n"
    ),
    "/srv/app/notes.txt": "Учебные заметки\nПроверить p95\n",
}
ROOT_DIRS = ("/srv", "/srv/app")


def list_http() -> list[HttpExercise]:
    return [HttpExercise(**item) for item in HTTP_EXERCISES]


def check_http(exercise_id: str, method: str, path: str) -> CheckResult:
    exercise = next((item for item in HTTP_EXERCISES if item["id"] == exercise_id), None)
    if exercise is None:
        return CheckResult(correct=False, feedback="Упражнение не найдено")
    normalized_method = method.strip().upper()
    normalized_path = path.strip()
    correct = normalized_method == exercise["method"] and normalized_path == exercise["path"]
    expected = f"{exercise['method']} {exercise['path']}"
    feedback = (
        "Верно. Запрос составлен по заданию."
        if correct
        else f"Пока не то. Ожидается {expected}. Подсказка: {exercise['hint']}"
    )
    return CheckResult(correct=correct, feedback=feedback, expected=expected)


def list_sql() -> list[SqlExercise]:
    return [
        SqlExercise(id=item["id"], title=item["title"], task=item["task"], hint=item["hint"])
        for item in SQL_EXERCISES
    ]


def _unsafe_sql(query: str) -> str | None:
    lowered = query.lower()
    if "u&" in lowered:
        return "Unicode-идентификаторы в SQL-тренажёре запрещены."
    if ";" in query or "--" in query or "/*" in query or "*/" in query:
        return "Разрешён один SELECT без комментариев и точек с запятой."
    if not re.match(r"^\s*select\b", lowered):
        return "Разрешён только SELECT."
    forbidden = (
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "vacuum",
        "analyze",
        "call",
        "do",
        "pg_",
        "information_schema",
        "current_user",
        "session_user",
        "set_config",
        "dblink",
        "lo_import",
        "generate_series",
        "current_database",
        "current_setting",
        "setval",
        "nextval",
        "lo_from_bytea",
        "lo_export",
        "pg_read_file",
        "for update",
        "for share",
        "advisory",
        "txid_",
    )
    for word in forbidden:
        if word in lowered:
            return f"Запрещённое слово: {word}."
    # Разрешены только три учебные таблицы. Проверяем все чувствительные имена
    # целиком, включая запятую, кавычки и подзапросы: одного regex после FROM мало.
    protected_tables = (
        "users",
        "sessions",
        "lesson_progress",
        "lesson_blocks",
        "quizzes",
        "quiz_questions",
        "quiz_options",
        "quiz_attempts",
        "quiz_attempt_answers",
        "quiz_attempt_selected_options",
        "lesson_notes",
        "lesson_highlights",
        "saved_questions",
        "review_items",
        "cheatsheets",
        "ai_teacher_messages",
        "alembic_version",
    )
    for table in protected_tables:
        if re.search(rf"\b{table}\b", lowered):
            return "В тренажёре можно использовать только courses, modules и lessons."
    return None


def _sqlite_sandbox(db: Session, deadline: float) -> sqlite3.Connection:
    """Создаёт песочницу и закрывает её при любой ошибке подготовки."""
    connection = sqlite3.connect(":memory:")
    try:
        return _populate_sandbox(connection, db, deadline)
    except Exception:
        connection.close()
        raise


def _populate_sandbox(
    connection: sqlite3.Connection, db: Session, deadline: float
) -> sqlite3.Connection:
    connection.executescript(
        """
        CREATE TABLE courses (
            id INTEGER PRIMARY KEY, slug TEXT, title TEXT,
            description TEXT, is_published INTEGER
        );
        CREATE TABLE modules (
            id INTEGER PRIMARY KEY, course_id INTEGER, title TEXT,
            summary TEXT, position INTEGER
        );
        CREATE TABLE lessons (
            id INTEGER PRIMARY KEY, module_id INTEGER, title TEXT,
            summary TEXT, estimated_minutes INTEGER, position INTEGER,
            is_published INTEGER
        );
        """
    )
    courses = list(db.scalars(select(Course).where(Course.is_published.is_(True))))
    modules = list(db.scalars(select(Module).join(Course).where(Course.is_published.is_(True))))
    lessons = list(
        db.scalars(
            select(Lesson)
            .join(Module)
            .join(Course)
            .where(Lesson.is_published.is_(True), Course.is_published.is_(True))
        )
    )
    connection.executemany(
        "INSERT INTO courses VALUES (?, ?, ?, ?, ?)",
        [
            (item.id, item.slug, item.title, item.description, int(item.is_published))
            for item in courses
        ],
    )
    connection.executemany(
        "INSERT INTO modules VALUES (?, ?, ?, ?, ?)",
        [(item.id, item.course_id, item.title, item.summary, item.position) for item in modules],
    )
    connection.executemany(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                item.id,
                item.module_id,
                item.title,
                item.summary,
                item.estimated_minutes,
                item.position,
                int(item.is_published),
            )
            for item in lessons
        ],
    )
    if time.monotonic() > deadline:
        raise TimeoutError
    connection.commit()
    connection.execute("PRAGMA query_only = ON")

    allowed_tables = {"courses", "modules", "lessons"}
    allowed_functions = {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "round",
        "lower",
        "upper",
        "length",
        "coalesce",
        "ifnull",
        "abs",
        "substr",
        "like",
        "glob",
    }

    def authorizer(action: int, arg1: str | None, arg2: str | None, *_args: object) -> int:
        if action == sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if arg1 in allowed_tables else sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_RECURSIVE):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION:
            return (
                sqlite3.SQLITE_OK
                if (arg2 or "").lower() in allowed_functions
                else sqlite3.SQLITE_DENY
            )
        return sqlite3.SQLITE_DENY

    connection.set_authorizer(authorizer)
    connection.set_progress_handler(
        lambda: 1 if time.monotonic() > deadline else 0,
        10_000,
    )
    return connection


def run_sql(db: Session, exercise_id: str, query: str) -> SqlResult:
    exercise = next((item for item in SQL_EXERCISES if item["id"] == exercise_id), None)
    if exercise is None:
        return SqlResult(columns=[], rows=[], correct=False, feedback="Упражнение не найдено")
    unsafe = _unsafe_sql(query)
    if unsafe:
        return SqlResult(columns=[], rows=[], correct=False, feedback=unsafe)
    deadline = time.monotonic() + 2
    try:
        connection = _sqlite_sandbox(db, deadline)
    except Exception:
        return SqlResult(
            columns=[],
            rows=[],
            correct=False,
            feedback="Не удалось подготовить учебные данные.",
        )
    try:
        result = connection.execute(f"SELECT * FROM ({query}) AS trainer_result LIMIT 50")
        columns = [column[0] for column in result.description or []]
        rows = []
        total_chars = 0
        while len(rows) < 50:
            row = result.fetchone()
            if row is None:
                break
            rows.append([value for value in row])
            total_chars += sum(len(str(value)) for value in row)
            if total_chars > 100_000:
                return SqlResult(
                    columns=[],
                    rows=[],
                    correct=False,
                    feedback="Результат слишком большой для тренажёра.",
                )
            if time.monotonic() > deadline:
                return SqlResult(
                    columns=[],
                    rows=[],
                    correct=False,
                    feedback="Запрос выполнялся слишком долго.",
                )
    except sqlite3.Error as error:
        timed_out = "interrupt" in str(error).lower()
        return SqlResult(
            columns=[],
            rows=[],
            correct=False,
            feedback=(
                "Запрос выполнялся слишком долго."
                if timed_out
                else "Запрос не выполнился. Проверьте названия таблиц и столбцов."
            ),
        )
    finally:
        connection.close()
    first = str(rows[0][0]) if rows and rows[0] else ""
    shape_ok = len(rows) == 1 and len(rows[0]) == 1
    correct = shape_ok and first.strip() == exercise["expected"]
    feedback = (
        "Верно."
        if correct
        else f"Запрос выполнился, но ответ другой. Ожидается: {exercise['expected']}."
    )
    return SqlResult(columns=columns, rows=rows, correct=correct, feedback=feedback)


def list_linux() -> list[LinuxExercise]:
    return [
        LinuxExercise(**{key: item[key] for key in ("id", "title", "task", "hint")})
        for item in LINUX_EXERCISES
    ]


def _resolve(path: str, cwd: str) -> str:
    if path.startswith("/"):
        parts = [part for part in path.split("/") if part]
        return "/" + "/".join(parts)
    parts = [part for part in (cwd + "/" + path).split("/") if part]
    return "/" + "/".join(parts)


def _ls(path: str) -> str:
    prefix = path.rstrip("/") + "/"
    children: set[str] = set()
    for file_path in FILES:
        if file_path.startswith(prefix):
            rest = file_path[len(prefix) :]
            children.add(rest.split("/", 1)[0])
    for directory in ROOT_DIRS:
        if directory.startswith(prefix) and directory != path.rstrip("/"):
            rest = directory[len(prefix) :]
            if rest:
                children.add(rest.split("/", 1)[0])
    return "\n".join(sorted(children))


def run_linux(exercise_id: str, command: str, cwd: str = "/srv/app") -> LinuxResult:
    exercise = next((item for item in LINUX_EXERCISES if item["id"] == exercise_id), None)
    if exercise is None:
        return LinuxResult(output="", cwd=cwd, correct=False, feedback="Упражнение не найдено")
    try:
        parts = shlex.split(command)
    except ValueError:
        return LinuxResult(
            output="", cwd=cwd, correct=False, feedback="Не удалось разобрать команду"
        )
    if not parts:
        return LinuxResult(output="", cwd=cwd, correct=False, feedback="Введите команду")
    name, args = parts[0], parts[1:]
    output = ""
    new_cwd = cwd
    if name == "pwd":
        output = cwd
    elif name == "cd" and args:
        new_cwd = _resolve(args[0], cwd)
        if new_cwd not in ROOT_DIRS:
            return LinuxResult(
                output="", cwd=cwd, correct=False, feedback="Такой папки нет в тренажёре"
            )
    elif name == "ls":
        output = _ls(_resolve(args[0], cwd) if args else cwd)
    elif name == "cat" and args:
        output = FILES.get(_resolve(args[0], cwd), "Нет такого файла")
    elif name == "grep" and len(args) >= 2:
        pattern = args[0]
        content = FILES.get(_resolve(args[1], cwd), "")
        output = "\n".join(line for line in content.splitlines() if pattern in line)
    elif name == "tail" and args:
        count = 10
        if args[0] == "-n" and len(args) >= 2:
            try:
                count = int(args[1])
            except ValueError:
                return LinuxResult(
                    output="",
                    cwd=cwd,
                    correct=False,
                    feedback="После -n нужно целое число строк.",
                )
            args = args[2:]
        content = FILES.get(_resolve(args[0], cwd), "") if args else ""
        output = "\n".join(content.splitlines()[-count:])
    else:
        output = "Команда не поддерживается в тренажёре"
    correct = (
        exercise["expected"] in output
        and name == exercise["command"]
        and (
            "expected_lines" not in exercise
            or len(output.splitlines()) == exercise["expected_lines"]
        )
    )
    feedback = "Верно." if correct else f"Ожидается вывод, содержащий: {exercise['expected']}."
    return LinuxResult(output=output, cwd=new_cwd, correct=correct, feedback=feedback)


def list_analysis() -> list[AnalysisExercise]:
    return [
        AnalysisExercise(
            id=item["id"],
            title=item["title"],
            situation=item["situation"],
            options=item["options"],
        )
        for item in ANALYSIS
    ]


def check_analysis(exercise_id: str, option_index: int) -> AnalysisResult:
    exercise = next((item for item in ANALYSIS if item["id"] == exercise_id), None)
    if exercise is None:
        return AnalysisResult(correct=False, feedback="Сценарий не найден")
    correct = option_index == exercise["correct"]
    return AnalysisResult(
        correct=correct,
        feedback=("Верно. " if correct else "Неверно. ") + exercise["feedback"],
    )
