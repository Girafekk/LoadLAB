"""Обезличивание текста перед отправкой внешнему AI."""

from __future__ import annotations

import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
URL = re.compile(r"https?://\S+", re.IGNORECASE)
TOKEN = re.compile(r"\b(?:Bearer|token|api[_-]?key)\s+[A-Za-z0-9._\-]{12,}", re.IGNORECASE)
LONG_ID = re.compile(r"\b\d{11,}\b")


def anonymize(text: str) -> str:
    """Убирает контакты, ссылки и длинные идентификаторы, сохраняя смысл."""
    value = EMAIL.sub("[email]", text)
    value = PHONE.sub("[телефон]", value)
    value = URL.sub("[ссылка]", value)
    value = TOKEN.sub("[секрет]", value)
    value = LONG_ID.sub("[номер]", value)
    return value
