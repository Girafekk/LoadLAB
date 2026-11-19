"""Контракты AI Teacher."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.tools import CleanText


class AiQuestion(BaseModel):
    lesson_id: int
    question: CleanText = Field(max_length=1_000)


class AiAnswer(BaseModel):
    answer: str
    mode: str
    provider: str
    lesson_id: int


class AiHistoryItem(BaseModel):
    id: int
    question: str
    answer: str
    mode: str
    created_at: datetime


class AiRecommendation(BaseModel):
    lesson_id: int
    title: str
    percent: int
    reason: str


class CheatsheetSuggestion(BaseModel):
    title: str
    content: str
    lesson_ids: list[int]
