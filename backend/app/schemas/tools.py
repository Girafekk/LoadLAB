"""Формы данных инструментов ученика: конспект, выделения, вопросы, повторение, шпаргалки."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

NOTE_MAX_LENGTH = 20_000
HIGHLIGHT_MAX_LENGTH = 1_000
QUESTION_MAX_LENGTH = 2_000
REVIEW_TITLE_MAX_LENGTH = 300
CHEATSHEET_TITLE_MAX_LENGTH = 200
CHEATSHEET_MAX_LENGTH = 20_000


# Управляющие символы PostgreSQL не принимает в тексте: без проверки запись
# упала бы с 500 вместо понятной ошибки 422.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _reject_control_chars(value: str) -> None:
    if _CONTROL_CHARS.search(value):
        raise ValueError("Текст содержит недопустимые управляющие символы")


def _not_blank(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Текст не может быть пустым")
    _reject_control_chars(cleaned)
    return cleaned


def _clean_note(value: str) -> str:
    """Конспект может быть пустым, но управляющие символы запрещены."""
    _reject_control_chars(value)
    return value


CleanText = Annotated[str, AfterValidator(_not_blank)]
NoteContent = Annotated[str, AfterValidator(_clean_note)]


def _clean_optional(value: str | None) -> str | None:
    return None if value is None else _not_blank(value)


CleanOptionalText = Annotated[str | None, AfterValidator(_clean_optional)]


class LessonNoteRead(BaseModel):
    """Конспект по уроку. Пустой конспект — это тоже ответ, а не 404."""

    lesson_id: int
    content: str
    updated_at: datetime | None


class LessonNoteUpdate(BaseModel):
    content: NoteContent = Field(max_length=NOTE_MAX_LENGTH)


class LessonHighlightCreate(BaseModel):
    text: CleanText = Field(min_length=1, max_length=HIGHLIGHT_MAX_LENGTH)


class LessonHighlightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    text: str
    created_at: datetime


class SavedQuestionCreate(BaseModel):
    text: CleanText = Field(min_length=1, max_length=QUESTION_MAX_LENGTH)
    lesson_id: int | None = None


class SavedQuestionUpdate(BaseModel):
    is_resolved: bool


class SavedQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int | None
    text: str
    is_resolved: bool
    created_at: datetime
    updated_at: datetime


class ReviewItemCreate(BaseModel):
    title: CleanText = Field(min_length=1, max_length=REVIEW_TITLE_MAX_LENGTH)
    note: CleanOptionalText = Field(default=None, max_length=QUESTION_MAX_LENGTH)
    lesson_id: int | None = None


class ReviewItemUpdate(BaseModel):
    is_done: bool


class ReviewItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int | None
    title: str
    note: str | None
    is_done: bool
    created_at: datetime
    updated_at: datetime


class CheatsheetCreate(BaseModel):
    title: CleanText = Field(min_length=1, max_length=CHEATSHEET_TITLE_MAX_LENGTH)
    content: CleanText = Field(min_length=1, max_length=CHEATSHEET_MAX_LENGTH)
    lesson_id: int | None = None


class CheatsheetUpdate(BaseModel):
    title: CleanOptionalText = Field(
        default=None, min_length=1, max_length=CHEATSHEET_TITLE_MAX_LENGTH
    )
    content: CleanOptionalText = Field(default=None, min_length=1, max_length=CHEATSHEET_MAX_LENGTH)


class CheatsheetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int | None
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class WeakTopicRead(BaseModel):
    """Тема, где лучший результат ученика ниже порога."""

    lesson_id: int
    lesson_title: str
    module_title: str
    best_percent: int
    attempts: int
