from sqlalchemy import BigInteger, Boolean, CheckConstraint, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin

USER_ROLES = ("student", "admin")
_ROLES_SQL = ", ".join(f"'{role}'" for role in USER_ROLES)


class User(TimestampMixin, Base):
    """Пользователь платформы: ученик или администратор."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"role IN ({_ROLES_SQL})", name="role"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Хранится только хэш пароля, сам пароль — никогда.
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student", server_default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
