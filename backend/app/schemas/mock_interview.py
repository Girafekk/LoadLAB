"""Контракты пробного собеседования."""

from datetime import datetime

from pydantic import BaseModel, Field


class MockQuestion(BaseModel):
    answer_id: int
    question_id: int | None
    text: str
    topic: str | None
    position: int


class MockSession(BaseModel):
    id: int
    status: str
    score: int
    total: int
    current: MockQuestion | None


class MockAnswerResult(BaseModel):
    answer_id: int
    score: int
    feedback: str
    completed: bool
    next_question: MockQuestion | None


class MockAnswerRead(BaseModel):
    position: int
    question: str
    answer: str | None
    feedback: str | None
    score: int | None


class MockReport(BaseModel):
    id: int
    status: str
    score: int
    total: int
    created_at: datetime
    completed_at: datetime | None
    answers: list[MockAnswerRead]
    current: MockQuestion | None = None


class MockAnswerInput(BaseModel):
    answer: str = Field(min_length=1, max_length=6_000)
    answer_id: int
    allow_external: bool = False
