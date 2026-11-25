"""API-тесты импорта курса: доступ и понятная ошибка файла."""

from sqlalchemy import update

from app.models import User
from tests.api.helpers import register


def _admin(api_client, db_session) -> None:
    response = register(api_client, email="admin-import@example.com")
    assert response.status_code == 201
    db_session.execute(
        update(User).where(User.email == "admin-import@example.com").values(role="admin")
    )


def test_import_requires_admin(api_client):
    response = api_client.post(
        "/api/v1/admin/course-imports/preview",
        files={"file": ("course.txt", b"# Course\n## Module\n### Lesson\nText", "text/plain")},
    )
    assert response.status_code == 401


def test_import_rejects_broken_pdf(api_client, db_session):
    _admin(api_client, db_session)
    response = api_client.post(
        "/api/v1/admin/course-imports/preview",
        files={"file": ("broken.pdf", b"not a pdf" * 100, "application/pdf")},
    )
    assert response.status_code == 422
    assert "PDF" in response.text or "файл" in response.text.lower()
