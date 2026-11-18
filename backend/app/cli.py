"""Служебные команды LoadLab.

Запуск (из папки backend):

    python -m app.cli create_admin
"""

import sys
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.schemas.user import UserCreate
from app.services import auth_service


def create_admin(db: Session) -> int:
    """Создаёт администратора. Возвращает код завершения: 0 — успех, 1 — ошибка."""
    email = input("Email администратора: ")
    # getpass не показывает ввод на экране, и пароль не остаётся в истории команд.
    password = getpass("Пароль (не короче 8 символов): ")
    if password != getpass("Пароль ещё раз: "):
        print("Ошибка: пароли не совпадают.", file=sys.stderr)
        return 1

    try:
        data = UserCreate(email=email, password=password)
    except ValidationError as error:
        # Печатаем только текст правил, без введённых значений.
        for problem in error.errors():
            print(f"Ошибка: {problem['loc'][0]} — {problem['msg']}", file=sys.stderr)
        return 1

    try:
        user = auth_service.register_user(db, data.email, data.password, role="admin")
    except auth_service.EmailAlreadyRegisteredError:
        print("Ошибка: пользователь с таким email уже существует.", file=sys.stderr)
        return 1

    print(f"Администратор создан: {user.email}")
    return 0


COMMANDS = {"create_admin": create_admin}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print(f"Использование: python -m app.cli <{' | '.join(COMMANDS)}>", file=sys.stderr)
        return 2
    with Session(get_engine()) as db:
        return COMMANDS[argv[0]](db)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
