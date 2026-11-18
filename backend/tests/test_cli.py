import pytest
from sqlalchemy import func, select

from app import cli
from app.core.security import verify_password
from app.models import User


@pytest.fixture
def answers(monkeypatch):
    """Подменяет ввод с клавиатуры: email и два ввода пароля."""

    def provide(email: str, password: str, repeat: str | None = None) -> None:
        passwords = iter([password, password if repeat is None else repeat])
        monkeypatch.setattr("builtins.input", lambda prompt="": email)
        monkeypatch.setattr(cli, "getpass", lambda prompt="": next(passwords))

    return provide


def test_create_admin(db_session, answers, capsys):
    answers(" Admin@Example.com ", "long-enough-password")

    assert cli.create_admin(db_session) == 0

    admin = db_session.scalar(select(User))
    assert admin.email == "admin@example.com"
    assert admin.role == "admin"
    assert verify_password("long-enough-password", admin.password_hash)
    assert "long-enough-password" not in capsys.readouterr().out


def test_create_admin_rejects_mismatched_and_short_passwords(db_session, answers, capsys):
    answers("admin@example.com", "long-enough-password", repeat="another-password")
    assert cli.create_admin(db_session) == 1

    answers("admin@example.com", "abc12")
    assert cli.create_admin(db_session) == 1

    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert "abc12" not in capsys.readouterr().err


def test_create_admin_rejects_existing_email(db_session, answers):
    answers("admin@example.com", "long-enough-password")
    assert cli.create_admin(db_session) == 0

    answers("Admin@example.com", "long-enough-password")
    assert cli.create_admin(db_session) == 1
    assert db_session.scalar(select(func.count()).select_from(User)) == 1


def test_unknown_command_prints_usage(capsys):
    assert cli.main(["drop_everything"]) == 2
    assert "create_admin" in capsys.readouterr().err
