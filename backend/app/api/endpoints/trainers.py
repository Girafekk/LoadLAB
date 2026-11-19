"""Интерактивные тренажёры для ученика."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import trainer_sql_rate_limiter
from app.db.session import get_db
from app.models import User
from app.schemas.trainers import (
    AnalysisCheck,
    AnalysisExercise,
    AnalysisResult,
    CheckResult,
    HttpCheck,
    HttpExercise,
    LinuxExercise,
    LinuxResult,
    LinuxRun,
    SqlExercise,
    SqlResult,
    SqlRun,
)
from app.services import trainers_service

router = APIRouter(prefix="/trainers", tags=["Тренажёры"])


@router.get("/http", response_model=list[HttpExercise], summary="Упражнения HTTP")
def http_exercises(user: User = Depends(get_current_user)) -> list[HttpExercise]:
    return trainers_service.list_http()


@router.post("/http/check", response_model=CheckResult, summary="Проверить HTTP-запрос")
def check_http(data: HttpCheck, user: User = Depends(get_current_user)) -> CheckResult:
    return trainers_service.check_http(data.exercise_id, data.method, data.path)


@router.get("/sql", response_model=list[SqlExercise], summary="Упражнения SQL")
def sql_exercises(user: User = Depends(get_current_user)) -> list[SqlExercise]:
    return trainers_service.list_sql()


@router.post("/sql/run", response_model=SqlResult, summary="Выполнить учебный SELECT")
def run_sql(
    data: SqlRun, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SqlResult:
    retry_after = trainer_sql_rate_limiter.reserve_attempt(f"sql-trainer:{user.id}")
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Слишком много SQL-запросов. Подождите немного.",
            headers={"Retry-After": str(retry_after)},
        )
    return trainers_service.run_sql(db, data.exercise_id, data.query)


@router.get("/linux", response_model=list[LinuxExercise], summary="Упражнения Linux")
def linux_exercises(user: User = Depends(get_current_user)) -> list[LinuxExercise]:
    return trainers_service.list_linux()


@router.post("/linux/run", response_model=LinuxResult, summary="Выполнить команду в тренажёре")
def run_linux(data: LinuxRun, user: User = Depends(get_current_user)) -> LinuxResult:
    return trainers_service.run_linux(data.exercise_id, data.command, data.cwd)


@router.get("/analysis", response_model=list[AnalysisExercise], summary="Сценарии анализа")
def analysis_exercises(user: User = Depends(get_current_user)) -> list[AnalysisExercise]:
    return trainers_service.list_analysis()


@router.post("/analysis/check", response_model=AnalysisResult, summary="Проверить анализ")
def check_analysis(data: AnalysisCheck, user: User = Depends(get_current_user)) -> AnalysisResult:
    return trainers_service.check_analysis(data.exercise_id, data.option_index)
