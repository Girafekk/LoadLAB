"""Административный разбор материалов собеседований."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import InterviewQuestion, InterviewSource, User
from app.schemas.interview import (
    AnalyzeResult,
    InterviewQuestionRead,
    InterviewQuestionUpdate,
    InterviewReport,
    InterviewSourceRead,
    LessonOption,
)
from app.services import interview_answers, interview_service

router = APIRouter(
    prefix="/admin/interview", tags=["Администрирование"], dependencies=[Depends(require_admin)]
)


@router.post("/sources", response_model=InterviewSourceRead, status_code=201)
def upload_source(
    file: Annotated[UploadFile, File()],
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InterviewSourceRead:
    try:
        return interview_service.save_source(db, user, file)
    except interview_service.InterviewTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except interview_service.InterviewError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/sources", response_model=list[InterviewSourceRead])
def list_sources(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[InterviewSourceRead]:
    sources = db.scalars(select(InterviewSource).order_by(InterviewSource.id.desc()))
    return [interview_service.source_read(db, source) for source in sources]


@router.post("/sources/{source_id}/analyze", response_model=AnalyzeResult)
def analyze_source(
    source_id: int,
    allow_external: bool = Query(default=False),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AnalyzeResult:
    source = db.get(InterviewSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Источник не найден")
    try:
        return interview_service.analyze_source(db, source, allow_external=allow_external)
    except interview_service.InterviewError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("/questions", response_model=list[InterviewQuestionRead])
def list_questions(
    status: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[InterviewQuestionRead]:
    query = select(InterviewQuestion).order_by(InterviewQuestion.id)
    if status:
        query = query.where(InterviewQuestion.status == status)
    if topic:
        query = query.where(InterviewQuestion.topic == topic)
    return [InterviewQuestionRead.model_validate(item) for item in db.scalars(query)]


@router.get("/questions/page", response_model=dict)
def question_page(
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    condition = InterviewQuestion.status == status if status else None
    count_query = select(func.count()).select_from(InterviewQuestion)
    query = select(InterviewQuestion).order_by(InterviewQuestion.id)
    if condition is not None:
        count_query = count_query.where(condition)
        query = query.where(condition)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.offset(offset).limit(limit)).all()
    return {
        "items": [InterviewQuestionRead.model_validate(item).model_dump() for item in items],
        "total": total,
    }


@router.patch("/questions/{question_id}", response_model=InterviewQuestionRead)
def update_question(
    question_id: int,
    data: InterviewQuestionUpdate,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InterviewQuestionRead:
    try:
        return interview_service.update_question(
            db,
            question_id,
            topic=data.topic,
            difficulty=data.difficulty,
            level=data.level,
            status=data.status,
            lesson_id=data.lesson_id,
            clear_lesson="lesson_id" in data.model_fields_set and data.lesson_id is None,
        )
    except interview_service.InterviewError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.get("/report", response_model=InterviewReport)
def report(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> InterviewReport:
    return interview_service.report(db)


@router.get("/lessons", response_model=list[LessonOption])
def lesson_options(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> list[LessonOption]:
    return [
        LessonOption(id=item.id, title=item.title) for item in interview_service.lesson_options(db)
    ]


@router.post("/reclassify")
def reclassify(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict[str, int]:
    return {"changed": interview_service.reclassify(db)}


@router.post("/approve-all")
def approve_all(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict[str, int]:
    return {"approved": interview_service.approve_all(db)}


@router.post("/deduplicate")
def deduplicate(
    user: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict[str, int]:
    return {"removed": interview_service.deduplicate(db)}


@router.post("/generate-answers")
def generate_answers(
    limit: int = Query(default=20, ge=1, le=50),
    allow_external: bool = Query(default=False),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return interview_answers.generate_answers(db, limit=limit, allow_external=allow_external)
