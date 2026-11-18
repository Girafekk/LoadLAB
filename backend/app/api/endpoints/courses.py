"""Публичная программа и личный прогресс."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.db.session import get_db
from app.models import User
from app.schemas.course import CourseOverview
from app.services.course_service import get_course_overview

router = APIRouter(prefix="/courses")


@router.get("/current", response_model=CourseOverview)
def read_current_course(
    user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)
) -> CourseOverview:
    course = get_course_overview(db, user.id if user else None)
    if course is None:
        raise HTTPException(status_code=404, detail="Курс не найден")
    return course
