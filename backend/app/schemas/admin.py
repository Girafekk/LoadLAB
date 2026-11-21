"""Административные формы: программа, уроки, блоки, квизы и прогресс учеников."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tools import CleanText

BlockType = Literal["heading", "text", "code", "callout", "image", "table", "list"]
QuestionKind = Literal["theory", "situation", "analysis", "error", "decision"]


class CourseCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    title: CleanText = Field(max_length=200)
    description: str | None = None


class CourseUpdate(BaseModel):
    title: CleanText | None = Field(default=None, max_length=200)
    description: str | None = None
    is_published: bool | None = None


class LessonBriefAdmin(BaseModel):
    id: int
    title: str
    position: int
    estimated_minutes: int
    is_published: bool
    quiz_id: int | None


class ModuleAdmin(BaseModel):
    id: int
    title: str
    summary: str | None
    position: int
    lessons: list[LessonBriefAdmin]


class CourseAdmin(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    is_published: bool
    module_count: int
    lesson_count: int


class CourseTree(CourseAdmin):
    modules: list[ModuleAdmin]


class ModuleCreate(BaseModel):
    title: CleanText = Field(max_length=200)
    summary: str | None = None


class ModuleUpdate(BaseModel):
    title: CleanText | None = Field(default=None, max_length=200)
    summary: str | None = None
    position: int | None = Field(default=None, ge=1)


class LessonCreate(BaseModel):
    title: CleanText = Field(max_length=200)
    summary: str | None = None
    estimated_minutes: int = Field(default=90, ge=5, le=600)


class LessonMove(BaseModel):
    direction: Literal["up", "down"]


class LessonUpdate(BaseModel):
    title: CleanText | None = Field(default=None, max_length=200)
    summary: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=5, le=600)
    position: int | None = Field(default=None, ge=1)
    is_published: bool | None = None


class BlockInput(BaseModel):
    type: BlockType
    content: dict[str, object]


class BlocksUpdate(BaseModel):
    blocks: list[BlockInput] = Field(max_length=100)


class BlockAdminRead(BlockInput):
    position: int


class LessonAdminRead(BaseModel):
    id: int
    module_id: int
    title: str
    summary: str | None
    estimated_minutes: int
    position: int
    is_published: bool
    blocks: list[BlockAdminRead]
    quiz_id: int | None


class QuizOptionAdmin(BaseModel):
    text: CleanText = Field(max_length=500)
    is_correct: bool


class QuizQuestionAdmin(BaseModel):
    kind: QuestionKind
    text: CleanText = Field(max_length=2_000)
    explanation: CleanText = Field(max_length=2_000)
    options: list[QuizOptionAdmin] = Field(min_length=2, max_length=8)


class QuizAdminPayload(BaseModel):
    title: CleanText = Field(max_length=200)
    description: str | None = None
    is_published: bool = False
    questions: list[QuizQuestionAdmin] = Field(min_length=1, max_length=30)
    # Явное подтверждение: замена вопросов удаляет попытки учеников.
    confirm_attempts_loss: bool = False
    # Версия, которую видел администратор: число попыток на момент открытия.
    expected_attempts_count: int | None = Field(default=None, ge=0)
    expected_quiz_id: int | None = None


class QuizAdminRead(BaseModel):
    id: int
    title: str
    description: str | None
    is_published: bool
    attempts_count: int
    questions: list[QuizQuestionAdmin]


class StudentProgress(BaseModel):
    id: int
    email: str
    completed_lessons: int
    total_lessons: int
    percent: int
    quiz_attempts: int
    last_activity: datetime | None


class ModuleProgress(BaseModel):
    module_id: int
    title: str
    completed: int
    total: int


class StudentProgressDetail(StudentProgress):
    modules: list[ModuleProgress]
