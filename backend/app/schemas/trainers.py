"""Контракты интерактивных тренажёров."""

from pydantic import BaseModel, Field


class HttpExercise(BaseModel):
    id: str
    title: str
    task: str
    method: str
    path: str
    hint: str


class HttpCheck(BaseModel):
    exercise_id: str
    method: str = Field(min_length=1, max_length=10)
    path: str = Field(min_length=1, max_length=300)


class CheckResult(BaseModel):
    correct: bool
    feedback: str
    expected: str | None = None


class SqlExercise(BaseModel):
    id: str
    title: str
    task: str
    hint: str


class SqlRun(BaseModel):
    exercise_id: str
    query: str = Field(min_length=1, max_length=2_000)


class SqlResult(BaseModel):
    columns: list[str]
    rows: list[list[object]]
    correct: bool
    feedback: str


class LinuxExercise(BaseModel):
    id: str
    title: str
    task: str
    hint: str


class LinuxRun(BaseModel):
    exercise_id: str
    command: str = Field(min_length=1, max_length=300)
    cwd: str = Field(default="/srv/app", max_length=200)


class LinuxResult(BaseModel):
    output: str
    cwd: str
    correct: bool
    feedback: str


class AnalysisExercise(BaseModel):
    id: str
    title: str
    situation: str
    options: list[str]


class AnalysisCheck(BaseModel):
    exercise_id: str
    option_index: int = Field(ge=0, le=10)


class AnalysisResult(BaseModel):
    correct: bool
    feedback: str
