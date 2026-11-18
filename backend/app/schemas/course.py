"""Контракт учебного каталога."""

from pydantic import BaseModel, ConfigDict


class LessonProgressState(BaseModel):
    completed_lessons: int
    total_lessons: int
    percent: int
    next_lesson_id: int | None
    last_completed_lesson_id: int | None


class LessonBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    position: int
    estimated_minutes: int
    is_completed: bool = False


class ModuleRead(BaseModel):
    id: int
    title: str
    summary: str | None
    position: int
    lessons: list[LessonBrief]


class CourseOverview(BaseModel):
    id: int
    slug: str
    title: str
    description: str | None
    modules: list[ModuleRead]
    progress: LessonProgressState | None


class LessonBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    content: dict[str, object]
    position: int


class LessonRead(BaseModel):
    id: int
    title: str
    summary: str | None
    estimated_minutes: int
    is_completed: bool
    blocks: list[LessonBlockRead]
