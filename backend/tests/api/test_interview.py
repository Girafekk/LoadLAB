"""Банк вопросов собеседований."""

from types import SimpleNamespace

from sqlalchemy import select, update

from app.db.content_loader import seed_content
from app.db.seed import seed_curriculum
from app.models import InterviewQuestion, Lesson, User
from app.services import interview_answers, interview_service
from tests.api.helpers import register


def _admin(api_client, db_session) -> None:
    register(api_client, email="interview-admin@example.com")
    db_session.execute(
        update(User).where(User.email == "interview-admin@example.com").values(role="admin")
    )
    db_session.flush()


def _upload(api_client, text: str, name: str = "interview.txt"):
    return api_client.post(
        "/api/v1/admin/interview/sources",
        files={"file": (name, text.encode(), "text/plain")},
    )


def test_interview_requires_admin(api_client):
    assert api_client.get("/api/v1/admin/interview/sources").status_code == 401
    register(api_client)
    assert api_client.get("/api/v1/admin/interview/sources").status_code == 403


def test_upload_analyze_and_report(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    text = (
        "1. Что такое RPS?\n2. Как найти узкое место в JMeter?\n3. Что такое p95?\n---\nне вопрос\n"
    )
    uploaded = _upload(api_client, text)
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["status"] == "extracted"
    source_id = body["id"]

    analyzed = api_client.post(f"/api/v1/admin/interview/sources/{source_id}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["questions_created"] >= 2

    questions = api_client.get("/api/v1/admin/interview/questions").json()
    assert len(questions) >= 2
    first = questions[0]
    patched = api_client.patch(
        f"/api/v1/admin/interview/questions/{first['id']}",
        json={"status": "approved", "topic": "Метрики"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "approved"

    report = api_client.get("/api/v1/admin/interview/report")
    assert report.status_code == 200
    data = report.json()
    assert data["total_questions"] >= 2
    assert data["approved"] == 1
    assert data["by_topic"]


def test_reference_answers_are_filled_for_new_questions(api_client, db_session, monkeypatch):
    _admin(api_client, db_session)
    question = InterviewQuestion(
        fingerprint="answer-test",
        text="Что такое RPS?",
        topic="Метрики",
        status="approved",
    )
    db_session.add(question)
    db_session.flush()
    monkeypatch.setattr(
        interview_answers.ai_teacher_service,
        "complete_external",
        lambda *args, **kwargs: (
            f'[{{"id": {question.id}, "answer": "RPS — запросы в секунду.", '
            '"criteria": ["Определение", "Пример", "Ограничение"]}]'
        ),
    )
    result = interview_answers.generate_answers(db_session, limit=1, allow_external=True)
    assert result["generated"] == 1
    db_session.refresh(question)
    assert question.reference_answer == "RPS — запросы в секунду."
    assert "Определение" in (question.answer_criteria or "")


def test_reference_answers_not_faked_without_provider(api_client, db_session, monkeypatch):
    _admin(api_client, db_session)
    question = InterviewQuestion(
        fingerprint="answer-none",
        text="Что такое p95?",
        topic="Метрики",
    )
    db_session.add(question)
    db_session.flush()
    monkeypatch.setattr(
        interview_answers.ai_teacher_service,
        "complete_external",
        lambda *args, **kwargs: None,
    )
    result = interview_answers.generate_answers(db_session, limit=1, allow_external=True)
    assert result["generated"] == 0
    assert result["fallback"] == 1
    db_session.refresh(question)
    assert question.reference_answer is None


def test_deduplicate_merges_near_duplicates(api_client, db_session):
    _admin(api_client, db_session)
    db_session.add_all(
        [
            InterviewQuestion(
                fingerprint="dup-a",
                text="Что такое RPS и как его измерить?",
                topic="Метрики",
                status="proposed",
            ),
            InterviewQuestion(
                fingerprint="dup-b",
                text="Что такое RPS и как его измерять?",
                topic="Метрики",
                status="approved",
                reference_answer="RPS — число запросов в секунду.",
                answer_criteria="- определение\n- формула",
            ),
        ]
    )
    db_session.flush()
    response = api_client.post("/api/v1/admin/interview/deduplicate")
    assert response.status_code == 200
    assert response.json()["removed"] == 1
    left = db_session.scalars(select(InterviewQuestion)).all()
    assert len(left) == 1
    assert left[0].status == "approved"
    assert left[0].reference_answer == "RPS — число запросов в секунду."
    assert "определение" in (left[0].answer_criteria or "")


def test_approve_all_and_reclassify(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    uploaded = _upload(api_client, "Что такое Kafka consumer group?\n")
    source_id = uploaded.json()["id"]
    api_client.post(f"/api/v1/admin/interview/sources/{source_id}/analyze")
    assert api_client.post("/api/v1/admin/interview/reclassify").status_code == 200
    approved = api_client.post("/api/v1/admin/interview/approve-all")
    assert approved.status_code == 200
    assert approved.json()["approved"] >= 1
    question = api_client.get("/api/v1/admin/interview/questions?status=approved").json()[0]
    assert question["topic"] == "Kafka"


def test_docx_upload_extracts_questions(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    from docx import Document

    path = tmp_path / "interview.docx"
    document = Document()
    document.add_paragraph("Что такое RPS?")
    document.add_paragraph("Как найти узкое место?")
    document.save(path)
    with path.open("rb") as handle:
        response = api_client.post(
            "/api/v1/admin/interview/sources",
            files={
                "file": (
                    "interview.docx",
                    handle.read(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert response.status_code == 201
    assert response.json()["status"] == "extracted"


def test_duplicate_question_across_sources(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    text = "Что такое RPS?\n"
    first = _upload(api_client, text, "a.txt")
    second = _upload(api_client, text, "b.txt")
    assert first.status_code == second.status_code == 201
    for item in (first, second):
        api_client.post(f"/api/v1/admin/interview/sources/{item.json()['id']}/analyze")

    questions = db_session.scalars(select(InterviewQuestion)).all()
    matching = [item for item in questions if "RPS" in item.text]
    assert len(matching) == 1
    assert matching[0].occurrences == 2


def test_upload_rejects_empty_and_bad_format(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    empty = _upload(api_client, "")
    assert empty.status_code == 422
    bad = api_client.post(
        "/api/v1/admin/interview/sources",
        files={"file": ("data.csv", b"a,b", "text/csv")},
    )
    assert bad.status_code == 422


def test_question_can_be_linked_to_lesson(api_client, db_session, tmp_path, monkeypatch):
    _admin(api_client, db_session)
    monkeypatch.setattr(
        interview_service,
        "get_settings",
        lambda: SimpleNamespace(interview_upload_dir=str(tmp_path)),
    )
    seed_curriculum(db_session)
    seed_content(db_session)
    db_session.commit()
    lesson_id = db_session.scalar(select(Lesson.id).order_by(Lesson.id))
    uploaded = _upload(api_client, "Что такое нагрузочное тестирование?\n")
    api_client.post(f"/api/v1/admin/interview/sources/{uploaded.json()['id']}/analyze")
    question = api_client.get("/api/v1/admin/interview/questions").json()[0]
    updated = api_client.patch(
        f"/api/v1/admin/interview/questions/{question['id']}",
        json={"lesson_id": lesson_id, "status": "approved"},
    )
    assert updated.status_code == 200
    assert updated.json()["lesson_id"] == lesson_id
    cleared = api_client.patch(
        f"/api/v1/admin/interview/questions/{question['id']}", json={"lesson_id": None}
    )
    assert cleared.status_code == 200
    assert cleared.json()["lesson_id"] is None
    report = api_client.get("/api/v1/admin/interview/report").json()
    assert not any(row["lesson_id"] == lesson_id for row in report["coverage"])
