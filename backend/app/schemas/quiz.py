"""Формы данных квиза: вопросы, попытки и результаты."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuizOptionRead(BaseModel):
    """Вариант ответа без признака правильности."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    position: int


class QuizQuestionRead(BaseModel):
    """Вопрос квиза. `multiple` подсказывает интерфейсу вид выбора."""

    id: int
    kind: str
    text: str
    position: int
    multiple: bool
    options: list[QuizOptionRead]


class QuizRead(BaseModel):
    """Квиз с вопросами, но без правильных ответов."""

    id: int
    title: str
    description: str | None
    questions: list[QuizQuestionRead]


class QuizAttemptSummary(BaseModel):
    """Короткая запись о попытке для истории."""

    id: int
    score: int
    max_score: int
    percent: int
    created_at: datetime


class QuizWithHistory(BaseModel):
    """Квиз урока и личная история попыток."""

    quiz: QuizRead
    attempts: list[QuizAttemptSummary]
    attempts_total: int
    best_percent: int | None


class QuizAnswerInput(BaseModel):
    """Ответ ученика на один вопрос."""

    question_id: int
    # Пустой список означает «не выбрано»; такой ответ считается неверным,
    # но требует явной отправки, а не пропуска вопроса.
    option_ids: list[int] = Field(min_length=1)


class QuizAttemptCreate(BaseModel):
    """Отправка квиза: ответ на каждый вопрос."""

    answers: list[QuizAnswerInput] = Field(min_length=1)
    client_token: str | None = Field(default=None, max_length=36)


class QuizQuestionResult(BaseModel):
    """Разбор одного вопроса после отправки."""

    question_id: int
    is_correct: bool
    selected_option_ids: list[int]
    correct_option_ids: list[int]
    explanation: str


class QuizAttemptResult(BaseModel):
    """Результат попытки с разбором ответов."""

    id: int
    score: int
    max_score: int
    percent: int
    created_at: datetime
    questions: list[QuizQuestionResult]
