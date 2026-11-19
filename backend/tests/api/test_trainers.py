"""Интерактивные тренажёры."""

import pytest
from sqlalchemy import select, update

from app.db.seed import seed_curriculum
from app.models import Course, Lesson
from tests.api.helpers import register


def _prepare(api_client, db_session) -> None:
    seed_curriculum(db_session)
    db_session.execute(update(Course).values(is_published=True))
    first = db_session.scalar(select(Lesson).order_by(Lesson.id))
    assert first is not None
    db_session.execute(update(Lesson).where(Lesson.id == first.id).values(is_published=True))
    db_session.flush()
    register(api_client)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/v1/trainers/http", None),
        (
            "POST",
            "/api/v1/trainers/http/check",
            {"exercise_id": "x", "method": "GET", "path": "/"},
        ),
        ("GET", "/api/v1/trainers/sql", None),
        ("POST", "/api/v1/trainers/sql/run", {"exercise_id": "x", "query": "SELECT 1"}),
        ("GET", "/api/v1/trainers/linux", None),
        ("POST", "/api/v1/trainers/linux/run", {"exercise_id": "x", "command": "pwd"}),
        ("GET", "/api/v1/trainers/analysis", None),
        (
            "POST",
            "/api/v1/trainers/analysis/check",
            {"exercise_id": "x", "option_index": 0},
        ),
    ],
)
def test_trainers_require_login(api_client, method, path, body):
    response = api_client.request(method, path, json=body)
    assert response.status_code == 401


def test_http_trainer_checks_method_and_path(api_client, db_session):
    _prepare(api_client, db_session)

    exercises = api_client.get("/api/v1/trainers/http")
    assert exercises.status_code == 200
    assert len(exercises.json()) >= 3

    good = api_client.post(
        "/api/v1/trainers/http/check",
        json={"exercise_id": "http-search", "method": "GET", "path": "/api/products?q=монитор"},
    )
    assert good.status_code == 200
    assert good.json()["correct"] is True

    bad = api_client.post(
        "/api/v1/trainers/http/check",
        json={"exercise_id": "http-search", "method": "POST", "path": "/api/products"},
    )
    assert bad.json()["correct"] is False
    assert "GET" in bad.json()["feedback"]


def test_sql_trainer_runs_safe_select_and_rejects_writes(api_client, db_session):
    _prepare(api_client, db_session)

    good = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": (
                "SELECT count(*) FROM modules WHERE course_id = "
                "(SELECT id FROM courses WHERE slug = 'load-testing')"
            ),
        },
    )
    assert good.status_code == 200
    assert good.json()["rows"] == [[8]]
    assert good.json()["correct"] is True

    bad = api_client.post(
        "/api/v1/trainers/sql/run",
        json={"exercise_id": "sql-modules", "query": "DROP TABLE lessons"},
    )
    assert bad.json()["correct"] is False
    assert "SELECT" in bad.json()["feedback"]

    injection = api_client.post(
        "/api/v1/trainers/sql/run",
        json={"exercise_id": "sql-modules", "query": "SELECT 1; DROP TABLE lessons"},
    )
    assert injection.json()["correct"] is False

    private = api_client.post(
        "/api/v1/trainers/sql/run",
        json={"exercise_id": "sql-modules", "query": "SELECT email FROM users"},
    )
    assert private.json()["correct"] is False
    assert private.json()["rows"] == []

    comma_bypass = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": "SELECT * FROM courses, users",
        },
    )
    assert comma_bypass.json()["correct"] is False
    assert comma_bypass.json()["rows"] == []

    quoted_bypass = api_client.post(
        "/api/v1/trainers/sql/run",
        json={"exercise_id": "sql-modules", "query": 'SELECT * FROM "users"'},
    )
    assert quoted_bypass.json()["correct"] is False
    assert quoted_bypass.json()["rows"] == []

    sequence_write = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": "SELECT setval('lessons_id_seq', 1, false)",
        },
    )
    assert sequence_write.json()["correct"] is False
    assert sequence_write.json()["rows"] == []

    unicode_bypass = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": 'SELECT * FROM courses, U&"u\\0073ers"',
        },
    )
    assert unicode_bypass.json()["correct"] is False
    assert unicode_bypass.json()["rows"] == []

    file_read = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": "SELECT * FROM courses, U&\"p\\0067_read_file\"('/etc/passwd')",
        },
    )
    assert file_read.json()["correct"] is False
    assert file_read.json()["rows"] == []

    like = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-course",
            "query": "SELECT title FROM courses WHERE title LIKE '%тест%'",
        },
    )
    assert like.status_code == 200
    assert like.json()["rows"]

    heavy = api_client.post(
        "/api/v1/trainers/sql/run",
        json={
            "exercise_id": "sql-modules",
            "query": (
                "SELECT count(*) FROM lessons l1, lessons l2, lessons l3, "
                "lessons l4, lessons l5, lessons l6"
            ),
        },
    )
    assert heavy.json()["correct"] is False
    assert heavy.json()["rows"] == []


def test_linux_trainer_simulates_commands(api_client, db_session):
    _prepare(api_client, db_session)

    pwd = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-pwd", "command": "pwd"},
    )
    assert pwd.json()["output"] == "/srv/app"
    assert pwd.json()["correct"] is True

    grep = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-grep", "command": "grep ERROR /srv/app/app.log"},
    )
    assert "ERROR" in grep.json()["output"]
    assert grep.json()["correct"] is True

    wrong_command = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-grep", "command": "cat /srv/app/app.log"},
    )
    assert wrong_command.json()["correct"] is False

    bad_tail = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-tail", "command": "tail -n abc /srv/app/app.log"},
    )
    assert bad_tail.status_code == 200
    assert bad_tail.json()["correct"] is False

    one_line = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-tail", "command": "tail -n 1 /srv/app/app.log"},
    )
    assert one_line.json()["correct"] is False

    two_lines = api_client.post(
        "/api/v1/trainers/linux/run",
        json={"exercise_id": "linux-tail", "command": "tail -n 2 /srv/app/app.log"},
    )
    assert two_lines.json()["correct"] is True


def test_analysis_trainer_scores_scenarios(api_client, db_session):
    _prepare(api_client, db_session)

    correct = api_client.post(
        "/api/v1/trainers/analysis/check",
        json={"exercise_id": "an-rps", "option_index": 0},
    )
    assert correct.json()["correct"] is True

    wrong = api_client.post(
        "/api/v1/trainers/analysis/check",
        json={"exercise_id": "an-rps", "option_index": 1},
    )
    assert wrong.json()["correct"] is False
    assert "5 %" in wrong.json()["feedback"]
