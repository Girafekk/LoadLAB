"""Контракты банка вопросов собеседований."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    media_type: str
    size_bytes: int
    status: str
    error: str | None
    created_at: datetime
    questions_count: int


class InterviewQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    topic: str | None
    difficulty: str
    level: str
    status: str
    occurrences: int
    source_id: int | None
    lesson_id: int | None
    reference_answer: str | None
    answer_criteria: str | None


class InterviewQuestionUpdate(BaseModel):
    topic: str | None = Field(default=None, max_length=120)
    difficulty: str | None = None
    level: str | None = None
    status: str | None = None
    lesson_id: int | None = None


class TopicCount(BaseModel):
    topic: str
    questions: int
    lessons: int


class CoverageRow(BaseModel):
    lesson_id: int
    lesson_title: str
    questions: int


class InterviewReport(BaseModel):
    total_questions: int
    approved: int
    proposed: int
    rejected: int
    answers_ready: int
    answers_missing: int
    criteria_ready: int
    questions_without_lesson: int
    by_topic: list[TopicCount]
    coverage: list[CoverageRow]
    gaps: list[str]
    suggestions: list[str]


class AnalyzeResult(BaseModel):
    sources_processed: int
    questions_created: int
    duplicates: int
    provider: str


class LessonOption(BaseModel):
    id: int
    title: str
