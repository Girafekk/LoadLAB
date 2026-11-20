"""Загрузка и разбор материалов собеседований."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from difflib import SequenceMatcher
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Course, InterviewQuestion, InterviewSource, Lesson, Module, User
from app.schemas.interview import (
    AnalyzeResult,
    CoverageRow,
    InterviewQuestionRead,
    InterviewReport,
    InterviewSourceRead,
    TopicCount,
)
from app.services import ai_teacher_service

MAX_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg"}
QUESTION_START = re.compile(
    r"^(как|что|почему|зачем|какие|какой|какая|где|чем|сколько|расскажи|опиши|"
    r"можешь|объясни|в чём|приведи|назови)\b",
    re.IGNORECASE,
)
TOPIC_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"jmeter|thread group|listener|assertion|extractor|jsr223|groovy|beanshell", re.I
        ),
        "JMeter",
    ),
    (re.compile(r"jvm|heap|garbage|\bgc\b|fullgc|метаданн|дамп|профилир", re.I), "JVM и память"),
    (re.compile(r"kafka|consumer|producer|offset|партиц", re.I), "Kafka"),
    (re.compile(r"брокер|очеред|rabbit|асинхрон", re.I), "Брокеры очередей"),
    (re.compile(r"kubernetes|k8s|пod|контейнер|docker", re.I), "Kubernetes"),
    (
        re.compile(r"корреляц|параметризац|извлека|переменн|csv", re.I),
        "Корреляция и параметризация",
    ),
    (re.compile(r"p95|p99|перцентил|rps|throughput|время отклик|метрик|ошибк", re.I), "Метрики"),
    (re.compile(r"grafana|prometheus|мониторинг|лог|метрика", re.I), "Мониторинг"),
    (re.compile(r"sql|база данных|бд|запрос|индекс|postgres", re.I), "SQL и базы данных"),
    (re.compile(r"linux|bash|grep|tail|curl|ssh|команд", re.I), "Linux"),
    (re.compile(r"http|rest|json|api|протокол|tcp|udp|балансиров", re.I), "HTTP и сети"),
    (
        re.compile(r"нагрузочн.*тест|stress|spike|soak|стабильн|отказ", re.I),
        "Виды нагрузочных тестов",
    ),
    (re.compile(r"узк.*мест|бутылочн|оптимиз|архитектур|микросервис", re.I), "Поиск узких мест"),
    (
        re.compile(r"тестов.*данн|профил.*нагруз|нагрузочн.*модел|сценари", re.I),
        "Нагрузочная модель",
    ),
    (re.compile(r"отчёт|отчет|вывод|рекомендац", re.I), "Отчётность"),
    (re.compile(r"требован|sla|slo|методик", re.I), "Требования"),
    (re.compile(r"опыт|проект|команд|расскаж|работ|задач", re.I), "Опыт и процесс"),
)

TOPIC_ALIASES = {
    "SQL": "SQL и базы данных",
    "Базы данных": "SQL и базы данных",
    "База данных как узкое место": "SQL и базы данных",
    "JVM": "JVM и память",
    "Kafka и consumer group": "Kafka",
    "Инструменты и заглушки": "Заглушки и эмуляторы",
    "Инструменты нагрузочного тестирования": "Инструменты",
    "Асинхронное взаимодействие и брокеры сообщений": "Брокеры очередей",
    "Инфраструктура": "Kubernetes",
    "Требования к производительности": "Требования",
    "Метрики нагрузочного тестирования": "Метрики",
    "Нагрузочная модель и профили нагрузки": "Нагрузочная модель",
    "Ресурсы сервера": "Мониторинг",
    "Тестовые данные": "Нагрузочная модель",
    "Java для JMeter": "Java для JMeter",
    "Нагрузочное тестирование": "Виды нагрузочных тестов",
}
NON_GAP_TOPICS: set[str] = set()


def classify_topic(text: str) -> str | None:
    for pattern, topic in TOPIC_RULES:
        if pattern.search(text):
            return topic
    return None


def canonical_topic(topic: str | None, text: str) -> str:
    value = (topic or "").strip()
    value = TOPIC_ALIASES.get(value, value)
    if value:
        prefixes = (
            ("JMeter", "JMeter"),
            ("SQL", "SQL и базы данных"),
            ("База данных", "SQL и базы данных"),
            ("Мониторинг", "Мониторинг"),
            ("Ресурсы сервера", "Мониторинг"),
            ("HTTP", "HTTP и сети"),
            ("Сетевые", "HTTP и сети"),
            ("Метрик", "Метрики"),
            ("Java", "Java и JVM"),
            ("JVM", "JVM и память"),
            ("Архитектура", "Архитектура системы"),
            ("Планирование", "Процесс нагрузочного тестирования"),
            ("Виды", "Виды нагрузочных тестов"),
            ("Инструменты", "Инструменты"),
            ("Тестовые данные", "Нагрузочная модель"),
        )
        for prefix, canonical in prefixes:
            if value.startswith(prefix):
                return canonical
    if value and value != "Общее":
        return value
    return classify_topic(text) or "Опыт и процесс"


class InterviewError(Exception):
    """Ошибка загрузки или разбора материала."""


def _upload_dir() -> Path:
    path = Path(get_settings().interview_upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_text(path: Path, suffix: str) -> str:
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))
        return "\n".join(parts)
    if suffix in {".png", ".jpg", ".jpeg"}:
        import pytesseract
        from PIL import Image

        with Image.open(path) as image:
            return pytesseract.image_to_string(image, lang="rus+eng")
    raise InterviewError("Неподдерживаемый формат файла")


def _clean_line(line: str) -> str:
    value = line.strip()
    value = re.sub(r"^[-*•]\s*", "", value)
    value = re.sub(r"^\d+[.)]\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _clean_text(value: str) -> str:
    return value.replace("\x00", "").strip()


def _heuristic_questions(text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = _clean_line(raw)
        if len(line) < 12 or len(line) > 500:
            continue
        if line.startswith("---") or line.endswith(":"):
            continue
        if "?" not in line and not QUESTION_START.search(line):
            continue
        key = line.casefold()
        if key not in seen:
            seen.add(key)
            result.append(line)
    return result


def _lesson_choices(db: Session) -> list[Lesson]:
    return list(
        db.scalars(
            select(Lesson)
            .join(Module)
            .join(Course)
            .where(Lesson.is_published.is_(True), Course.is_published.is_(True))
            .order_by(Lesson.id)
        )
    )


def lesson_options(db: Session) -> list[Lesson]:
    """Опубликованные уроки для ручной привязки вопроса."""
    return _lesson_choices(db)


def _ai_questions(db: Session, text: str, lessons: list[Lesson]) -> list[dict[str, object]] | None:
    lesson_list = "\n".join(f"{item.id}: {item.title}" for item in lessons)
    system = (
        "Ты аналитик учебного контента. Извлеки из текста вопросы собеседования "
        "на Junior Load Tester. Верни только JSON-массив без Markdown. Каждый элемент: "
        '{"text": "...", "topic": "...", "difficulty": "junior|middle", '
        '"level": "base|extra|future", "lesson_id": число или null}. '
        "Не включай персональные данные, имена и контакты. Объединяй повторы."
    )
    valid_ids = {item.id for item in lessons}
    result: list[dict[str, object]] = []
    chunks = [text[index : index + 12_000] for index in range(0, len(text), 12_000)]
    for chunk in chunks[:10]:
        raw = ai_teacher_service.complete_external(
            system,
            f"Список уроков курса (id: название):\n{lesson_list}\n\nТекст материала:\n{chunk}",
            timeout=60,
        )
        if not raw:
            continue
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match is None:
            continue
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue
        for item in data:
            if not isinstance(item, dict):
                continue
            text_value = _clean_text(str(item.get("text", "")))[:1_000]
            if len(text_value) < 10:
                continue
            lesson_id = item.get("lesson_id")
            if not isinstance(lesson_id, int) or lesson_id not in valid_ids:
                lesson_id = None
            result.append(
                {
                    "text": text_value,
                    "topic": str(item.get("topic", "Общее"))[:120],
                    "difficulty": (
                        item.get("difficulty")
                        if item.get("difficulty") in {"junior", "middle"}
                        else "junior"
                    ),
                    "level": (
                        item.get("level")
                        if item.get("level") in {"base", "extra", "future"}
                        else "base"
                    ),
                    "lesson_id": lesson_id,
                }
            )
    return result or None


def _fingerprint(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip(" ?!.,;:")
    return hashlib.sha256(normalized.encode()).hexdigest()


def save_source(db: Session, user: User, upload: UploadFile) -> InterviewSource:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise InterviewError("Поддерживаются TXT, PDF, DOCX, PNG и JPG")
    content = upload.file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise InterviewError("Файл больше 10 МБ")
    if not content:
        raise InterviewError("Файл пустой")
    stored_name = hashlib.sha256(content).hexdigest()[:32] + "-" + uuid.uuid4().hex[:12] + suffix
    target = _upload_dir() / stored_name
    try:
        target.write_bytes(content)
    except OSError as error:
        raise InterviewError("Не удалось сохранить файл на сервере") from error
    source = InterviewSource(
        uploaded_by=user.id,
        filename=Path(upload.filename or "material").name[:255],
        stored_name=stored_name,
        media_type=upload.content_type or "application/octet-stream",
        size_bytes=len(content),
        status="uploaded",
    )
    db.add(source)
    db.flush()
    try:
        text = _extract_text(target, suffix)
        text = _clean_text(text)
        if not text:
            raise InterviewError("В файле не найден текст")
        source.text = text[:500_000]
        source.status = "extracted"
        source.error = None
    except Exception as error:
        source.status = "error"
        source.error = str(error)[:1_000]
    db.commit()
    db.refresh(source)
    if source.status == "error":
        raise InterviewError(source.error or "Не удалось извлечь текст")
    return source


def source_read(db: Session, source: InterviewSource) -> InterviewSourceRead:
    count = int(
        db.scalar(
            select(func.count())
            .select_from(InterviewQuestion)
            .where(InterviewQuestion.source_id == source.id)
        )
        or 0
    )
    return InterviewSourceRead(
        id=source.id,
        filename=source.filename,
        media_type=source.media_type,
        size_bytes=source.size_bytes,
        status=source.status,
        error=source.error,
        created_at=source.created_at,
        questions_count=count,
    )


def analyze_source(db: Session, source: InterviewSource) -> AnalyzeResult:
    if not source.text:
        raise InterviewError("Нет извлечённого текста")
    lessons = _lesson_choices(db)
    extracted = _ai_questions(db, source.text, lessons) or [
        {"text": text, "topic": "Общее", "difficulty": "junior", "level": "base", "lesson_id": None}
        for text in _heuristic_questions(source.text)
    ]
    # Повторный разбор источника не должен накапливать его же дубли.
    db.execute(
        InterviewQuestion.__table__.delete().where(
            InterviewQuestion.source_id == source.id,
            InterviewQuestion.status == "proposed",
        )
    )
    created = 0
    duplicates = 0
    for item in extracted:
        text = _clean_text(str(item["text"]))[:1_000]
        if len(text) < 10:
            continue
        fingerprint = _fingerprint(text)
        existing = db.scalar(
            select(InterviewQuestion).where(InterviewQuestion.fingerprint == fingerprint)
        )
        if existing is not None:
            existing.occurrences += 1
            duplicates += 1
            continue
        db.add(
            InterviewQuestion(
                fingerprint=fingerprint,
                text=text,
                topic=canonical_topic(str(item["topic"])[:120], text),
                difficulty=str(item["difficulty"]),
                level=str(item["level"]),
                source_id=source.id,
                lesson_id=item["lesson_id"],  # type: ignore[arg-type]
                status="proposed",
                occurrences=1,
            )
        )
        created += 1
    source.status = "analyzed"
    if len(source.text) > 120_000:
        source.error = (
            f"Материал длиннее 120 000 символов: разобраны первые 120 000 "
            f"(всего {len(source.text)})."
        )
    else:
        source.error = None
    db.commit()
    provider = "llm" if ai_teacher_service.provider_status().external else "local"
    return AnalyzeResult(
        sources_processed=1,
        questions_created=created,
        duplicates=duplicates,
        provider=provider,
    )


def update_question(
    db: Session,
    question_id: int,
    *,
    topic: str | None = None,
    difficulty: str | None = None,
    level: str | None = None,
    status: str | None = None,
    lesson_id: int | None = None,
    clear_lesson: bool = False,
) -> InterviewQuestionRead:
    question = db.get(InterviewQuestion, question_id)
    if question is None:
        raise InterviewError("Вопрос не найден")
    if topic is not None:
        question.topic = topic
    if difficulty in {"junior", "middle"}:
        question.difficulty = difficulty
    if level in {"base", "extra", "future"}:
        question.level = level
    if status in {"proposed", "approved", "rejected"}:
        question.status = status
    if clear_lesson:
        question.lesson_id = None
    elif lesson_id is not None:
        if db.get(Lesson, lesson_id) is None:
            raise InterviewError("Урок не найден")
        question.lesson_id = lesson_id
    db.commit()
    db.refresh(question)
    return InterviewQuestionRead.model_validate(question)


def reclassify(db: Session) -> int:
    """Приводит темы к каноническим, убирает «Общее» и привязывает очевидные уроки."""
    lessons = _lesson_choices(db)
    changed = 0
    for question in db.scalars(select(InterviewQuestion)):
        topic = canonical_topic(question.topic, question.text)
        if topic != question.topic:
            question.topic = topic
            changed += 1
        if question.lesson_id is None and topic not in NON_GAP_TOPICS:
            lesson_id = _guess_lesson(lessons, topic)
            if lesson_id is not None:
                question.lesson_id = lesson_id
                changed += 1
    db.commit()
    return changed


def _guess_lesson(lessons: list[Lesson], topic: str) -> int | None:
    words = [
        word
        for word in re.findall(r"[a-zA-Zа-яА-ЯёЁ]{3,}", topic.casefold())
        if word not in {"для", "или", "как", "что", "тест", "тесты"}
    ]
    if not words:
        return None
    best: tuple[int, int] | None = None
    for lesson in lessons:
        haystack = f"{lesson.title} {lesson.module.title}".casefold()
        score = sum(1 for word in words if word in haystack)
        if score and (best is None or score > best[0]):
            best = (score, lesson.id)
    return best[1] if best else None


def deduplicate(db: Session, threshold: float = 0.9) -> int:
    """Объединяет смысловые повторы, сохраняя лучший статус и число встреч."""
    questions = list(db.scalars(select(InterviewQuestion).order_by(InterviewQuestion.id)))
    normalized = [re.sub(r"\W+", " ", item.text.casefold()).strip() for item in questions]
    removed: set[int] = set()
    for index, question in enumerate(questions):
        if question.id in removed or len(normalized[index]) < 20:
            continue
        for other_index in range(index + 1, len(questions)):
            other = questions[other_index]
            if other.id in removed or len(normalized[other_index]) < 20:
                continue
            if (
                SequenceMatcher(None, normalized[index], normalized[other_index]).ratio()
                < threshold
            ):
                continue
            question.occurrences += other.occurrences
            if other.status == "approved":
                question.status = "approved"
            if question.lesson_id is None and other.lesson_id is not None:
                question.lesson_id = other.lesson_id
            if question.topic in {None, "Опыт и процесс"} and other.topic:
                question.topic = other.topic
            if not question.reference_answer and other.reference_answer:
                question.reference_answer = other.reference_answer
            if not question.answer_criteria and other.answer_criteria:
                question.answer_criteria = other.answer_criteria
            if question.source_id is None and other.source_id is not None:
                question.source_id = other.source_id
            if question.difficulty == "junior" and other.difficulty == "middle":
                question.difficulty = "middle"
            if question.level == "base" and other.level in {"extra", "future"}:
                question.level = other.level
            if other.status == "approved":
                question.status = "approved"
            removed.add(other.id)
            db.delete(other)
    db.commit()
    return len(removed)


def approve_all(db: Session) -> int:
    """Массовое подтверждение предложенных вопросов администратором."""
    questions = list(
        db.scalars(select(InterviewQuestion).where(InterviewQuestion.status == "proposed"))
    )
    for question in questions:
        question.status = "approved"
    db.commit()
    return len(questions)


def report(db: Session) -> InterviewReport:
    questions = list(db.scalars(select(InterviewQuestion)))
    approved = sum(1 for item in questions if item.status == "approved")
    proposed = sum(1 for item in questions if item.status == "proposed")
    rejected = sum(1 for item in questions if item.status == "rejected")
    answers_ready = sum(1 for item in questions if item.reference_answer and item.answer_criteria)
    criteria_ready = sum(1 for item in questions if item.answer_criteria)
    without_lesson = sum(1 for item in questions if item.lesson_id is None)
    topics: dict[str, list[InterviewQuestion]] = {}
    for item in questions:
        topics.setdefault(item.topic or "Без темы", []).append(item)
    by_topic = [
        TopicCount(
            topic=topic,
            questions=len(items),
            lessons=len({item.lesson_id for item in items if item.lesson_id}),
        )
        for topic, items in sorted(topics.items(), key=lambda pair: -len(pair[1]))
    ]
    coverage_rows = db.execute(
        select(Lesson.id, Lesson.title, func.count(InterviewQuestion.id))
        .join(InterviewQuestion, InterviewQuestion.lesson_id == Lesson.id)
        .group_by(Lesson.id, Lesson.title)
        .order_by(func.count(InterviewQuestion.id).desc())
    ).all()
    coverage = [
        CoverageRow(lesson_id=row[0], lesson_title=row[1], questions=row[2])
        for row in coverage_rows
    ]
    gaps = [
        topic
        for topic, items in topics.items()
        if topic not in NON_GAP_TOPICS and not any(item.lesson_id for item in items)
    ]
    suggestions = []
    for topic in gaps[:8]:
        suggestions.append(f"Добавить или расширить урок по теме «{topic}».")
    if approved == 0:
        suggestions.append("Подтвердить вопросы в банке, чтобы собрать пробное собеседование.")
    if not suggestions:
        suggestions.append("Покрытие тем достаточное; уточните сложность и формулировки.")
    return InterviewReport(
        total_questions=len(questions),
        approved=approved,
        proposed=proposed,
        rejected=rejected,
        answers_ready=answers_ready,
        answers_missing=len(questions) - answers_ready,
        criteria_ready=criteria_ready,
        questions_without_lesson=without_lesson,
        by_topic=by_topic,
        coverage=coverage,
        gaps=gaps,
        suggestions=suggestions,
    )
