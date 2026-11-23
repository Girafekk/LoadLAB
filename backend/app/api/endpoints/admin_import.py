"""Импорт курса из файла: предпросмотр и подтверждение."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.services import course_import_service as service

router = APIRouter(
    prefix="/admin/course-imports",
    dependencies=[Depends(require_admin)],
    tags=["Администрирование"],
)
MAX_BYTES = 10 * 1024 * 1024


@router.post("/preview", summary="Разобрать файл и показать черновик курса")
def preview(file: Annotated[UploadFile, File()]) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in service.ALLOWED:
        raise HTTPException(status_code=422, detail="Поддерживаются TXT, PDF, DOC и DOCX")
    content = file.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 10 МБ")
    upload_dir = Path(get_settings().interview_upload_dir).parent / "course_imports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_path = upload_dir / f"source-{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    try:
        text = service.extract_file(temp_path)
        token, draft = service.build_preview(temp_path, text, Path(file.filename or "Курс").stem)
    except service.CourseImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    finally:
        temp_path.unlink(missing_ok=True)
    return {"token": token, "course": draft, "source_chars": len(text)}


@router.delete("/{token}", status_code=204, summary="Отменить предпросмотр")
def cancel(token: str) -> None:
    try:
        service.delete_preview(token)
    except service.CourseImportError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.post("/{token}/approve", summary="Создать черновик курса из предпросмотра")
def approve(token: str, db: Session = Depends(get_db)) -> dict:
    try:
        course = service.approve_preview(db, token)
    except service.CourseImportError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return {
        "course_id": course.id,
        "title": course.title,
        "modules": len(course.modules),
        "lessons": sum(len(module.lessons) for module in course.modules),
    }
