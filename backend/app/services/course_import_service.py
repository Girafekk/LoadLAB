"""Импорт курса из файла: предпросмотр и создание черновика."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Course, Lesson, LessonBlock, Module
from app.services.ai_teacher_service import complete_external
from app.services.interview_service import InterviewError, _extract_text
from app.services.privacy import anonymize

ALLOWED = {".txt", ".md", ".pdf", ".doc", ".docx"}
MAX_CHARS = 80_000
MAX_MODULES = 12
MAX_LESSONS = 30
MAX_BLOCKS = 40
TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


class CourseImportError(Exception):
    """Файл не удалось разобрать."""


def slugify(value: str) -> str:
    value = value.casefold().translate(TRANSLIT)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:100] or "imported-course"


def _draft_dir() -> Path:
    path = Path(get_settings().interview_upload_dir).parent / "course_imports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _prompt(text: str) -> tuple[str, str]:
    system = (
        "Ты методист LMS LoadLab. Превращаешь учебный текст в черновик курса. "
        "Верни ТОЛЬКО JSON без Markdown. Схема: "
        '{"title":"...","description":"...","modules":[{"title":"...",'
        '"summary":"...","lessons":[{"title":"...","summary":"...",'
        '"blocks":[{"type":"text|callout|list|table|code","text":"...",'
        '"items":["..."],"headers":["..."],"rows":[["..."]],"language":"...",'
        '"code":"..."}]}]}]}. '
        "Не выдумывай факты. Сохраняй порядок и темы исходника. "
        "Делай 2–8 модулей и 1–12 уроков; в уроке 2–10 блоков. "
        "Не добавляй персональные данные. Пиши по-русски."
    )
    return system, f"Исходный материал:\n\n{text[:MAX_CHARS]}"


def _parse_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _clean_blocks(raw_blocks: Any) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if not isinstance(raw_blocks, list):
        return blocks
    for raw in raw_blocks[:MAX_BLOCKS]:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("type")
        if kind == "list":
            items = [
                str(item).strip()
                for item in (raw.get("items") if isinstance(raw.get("items"), list) else [])
                if str(item).strip()
            ]
            if items:
                blocks.append({"type": "list", "content": {"items": items[:20]}})
        elif kind == "table":
            headers = [
                str(item).strip()
                for item in (raw.get("headers") if isinstance(raw.get("headers"), list) else [])
            ]
            rows = [
                [str(item).strip() for item in row]
                for row in (raw.get("rows") if isinstance(raw.get("rows"), list) else [])
                if isinstance(row, list)
            ]
            if headers and rows:
                blocks.append({"type": "table", "content": {"headers": headers, "rows": rows[:30]}})
        elif kind == "code":
            code = str(raw.get("code", "")).strip()
            if code:
                blocks.append(
                    {
                        "type": "code",
                        "content": {
                            "language": str(raw.get("language", "text")),
                            "code": code[:20_000],
                        },
                    }
                )
        else:
            text = str(raw.get("text", "")).strip()
            if text:
                blocks.append(
                    {
                        "type": "callout" if kind == "callout" else "text",
                        "content": {"text": text[:20_000]},
                    }
                )
    return blocks


def _clean_course(data: dict[str, Any], fallback_title: str) -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    raw_modules = data.get("modules", [])
    if not isinstance(raw_modules, list):
        raw_modules = []
    for module_index, raw_module in enumerate(raw_modules[:MAX_MODULES], start=1):
        if not isinstance(raw_module, dict):
            continue
        title = str(raw_module.get("title", "")).strip()[:200]
        if not title:
            continue
        lessons = []
        raw_lessons = raw_module.get("lessons")
        if not isinstance(raw_lessons, list):
            raw_lessons = []
        for lesson_index, raw_lesson in enumerate(raw_lessons[:MAX_LESSONS], start=1):
            if not isinstance(raw_lesson, dict):
                continue
            lesson_title = str(raw_lesson.get("title", "")).strip()[:200]
            if not lesson_title:
                continue
            blocks = _clean_blocks(raw_lesson.get("blocks"))
            if not blocks:
                continue
            lessons.append(
                {
                    "title": lesson_title,
                    "summary": str(raw_lesson.get("summary", "")).strip()[:1000] or None,
                    "blocks": blocks,
                    "position": lesson_index,
                }
            )
        if lessons:
            modules.append(
                {
                    "title": title,
                    "summary": str(raw_module.get("summary", "")).strip()[:1000] or None,
                    "lessons": lessons,
                    "position": module_index,
                }
            )
    if not modules:
        raise CourseImportError("AI не смог выделить модули и уроки. Проверьте структуру файла.")
    return {
        "title": str(data.get("title", "")).strip()[:200] or fallback_title[:200],
        "description": str(data.get("description", "")).strip()[:2000] or None,
        "modules": modules,
    }


def _local_parse(text: str, fallback_title: str) -> dict[str, Any]:
    """Резервный разбор заголовков, если AI недоступен."""
    lines = [line.rstrip() for line in text.splitlines()]
    modules: list[dict[str, Any]] = []
    current_module: dict[str, Any] | None = None
    current_lesson: dict[str, Any] | None = None
    paragraphs: list[str] = []

    def flush_lesson() -> None:
        nonlocal current_lesson, paragraphs
        if current_lesson is None:
            return
        blocks = []
        for paragraph in paragraphs:
            if paragraph.startswith(("- ", "* ")):
                items = [
                    line[2:].strip() for line in paragraph.splitlines() if line[:2] in ("- ", "* ")
                ]
                if items:
                    blocks.append({"type": "list", "content": {"items": items}})
            else:
                blocks.append({"type": "text", "content": {"text": paragraph}})
        if blocks:
            current_lesson["blocks"] = blocks
            assert current_module is not None
            current_module["lessons"].append(current_lesson)
        current_lesson = None
        paragraphs = []

    parsed_title = fallback_title
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            parsed_title = stripped[2:].strip()[:200]
        elif stripped.startswith("#### "):
            if current_lesson is not None:
                paragraphs.append(stripped[5:].strip())
        elif stripped.startswith("## "):
            flush_lesson()
            if current_module and current_module["lessons"]:
                modules.append(current_module)
            current_module = {
                "title": stripped[3:][:200],
                "summary": None,
                "lessons": [],
            }
        elif stripped.startswith("### "):
            flush_lesson()
            if current_module is None:
                current_module = {"title": "Материал", "summary": None, "lessons": []}
            current_lesson = {"title": stripped[4:][:200], "summary": None, "blocks": []}
        elif current_lesson is not None:
            paragraphs.append(stripped)
        elif current_module is None:
            current_module = {"title": "Материал", "summary": None, "lessons": []}
    flush_lesson()
    if current_module and current_module["lessons"]:
        modules.append(current_module)
    for index, module in enumerate(modules, start=1):
        module["position"] = index
        for lesson_index, lesson in enumerate(module["lessons"], start=1):
            lesson["position"] = lesson_index
    if not modules:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        lessons = [
            {
                "title": f"Материал {index + 1}",
                "summary": None,
                "blocks": [{"type": "text", "content": {"text": p}}],
                "position": index + 1,
            }
            for index, p in enumerate(paragraphs[:20])
        ]
        modules = [
            {"title": fallback_title[:200], "summary": None, "lessons": lessons, "position": 1}
        ]
    return {
        "title": parsed_title[:200],
        "description": None,
        "modules": modules,
    }


def _cleanup_drafts() -> None:
    now = time.time()
    for draft in _draft_dir().glob("*"):
        try:
            if now - draft.stat().st_mtime > 24 * 60 * 60:
                draft.unlink(missing_ok=True)
        except OSError:
            continue


def cleanup_drafts() -> None:
    """Публичная точка для фонового janitor."""
    _cleanup_drafts()


def build_preview(path: Path, text: str, fallback_title: str) -> tuple[str, dict[str, Any]]:
    _cleanup_drafts()
    cleaned = text.strip()
    if len(cleaned) < 100:
        raise CourseImportError("В файле слишком мало текста для курса.")
    if len(cleaned) > MAX_CHARS:
        raise CourseImportError(
            f"В файле {len(cleaned)} символов, а поддерживается до {MAX_CHARS}. "
            "Разбейте материал на части."
        )
    data = _parse_json(complete_external(*_prompt(anonymize(cleaned)), timeout=90))
    try:
        draft = (
            _clean_course(data or {}, fallback_title)
            if data
            else _local_parse(cleaned, fallback_title)
        )
    except CourseImportError:
        draft = _local_parse(cleaned, fallback_title)
    token = uuid.uuid4().hex
    draft["source_name"] = fallback_title[:200]
    draft["used_ai"] = data is not None
    (_draft_dir() / f"{token}.json").write_text(
        json.dumps(draft, ensure_ascii=False), encoding="utf-8"
    )
    return token, draft


def read_preview(token: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{32}", token):
        raise CourseImportError("Некорректный предпросмотр.")
    path = _draft_dir() / f"{token}.json"
    if not path.exists():
        raise CourseImportError("Предпросмотр не найден или устарел.")
    if time.time() - path.stat().st_mtime > 24 * 60 * 60:
        path.unlink(missing_ok=True)
        raise CourseImportError("Предпросмотр устарел. Загрузите файл снова.")
    return json.loads(path.read_text(encoding="utf-8"))


def approve_preview(db: Session, token: str) -> Course:
    if not re.fullmatch(r"[a-f0-9]{32}", token):
        raise CourseImportError("Некорректный предпросмотр.")
    path = _draft_dir() / f"{token}.json"
    lock = _draft_dir() / f"{token}.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > 24 * 60 * 60:
            lock.unlink(missing_ok=True)
        if not path.exists():
            raise CourseImportError("Предпросмотр не найден или устарел.")
        if time.time() - path.stat().st_mtime > 24 * 60 * 60:
            path.unlink(missing_ok=True)
            raise CourseImportError("Предпросмотр устарел. Загрузите файл снова.")
        if lock.exists():
            raise CourseImportError("Предпросмотр уже создаётся или устарел.")
    except FileNotFoundError as error:
        raise CourseImportError("Предпросмотр уже создаётся или устарел.") from error
    try:
        path.replace(lock)
    except OSError as error:
        raise CourseImportError("Предпросмотр уже создаётся или устарел.") from error
    try:
        draft = json.loads(lock.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001
        lock.unlink(missing_ok=True)
        raise CourseImportError("Предпросмотр повреждён. Загрузите файл снова.") from error
    base_slug = slugify(draft["title"])
    slug = base_slug
    counter = 2
    while db.scalar(select(Course).where(Course.slug == slug)) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    course = Course(
        slug=slug,
        title=draft["title"],
        description=draft.get("description"),
        is_published=False,
    )
    db.add(course)
    db.flush()
    for module_data in draft["modules"]:
        module = Module(
            course_id=course.id,
            title=module_data["title"],
            summary=module_data.get("summary"),
            position=module_data["position"],
        )
        db.add(module)
        db.flush()
        for lesson_data in module_data["lessons"]:
            lesson = Lesson(
                module_id=module.id,
                title=lesson_data["title"],
                summary=lesson_data.get("summary"),
                content_key=f"import-{course.id}-{module.id}-{lesson_data['position']}",
                estimated_minutes=max(30, min(180, 30 * len(lesson_data["blocks"]))),
                position=lesson_data["position"],
                is_published=False,
            )
            db.add(lesson)
            db.flush()
            for position, block in enumerate(lesson_data["blocks"], start=1):
                db.add(
                    LessonBlock(
                        lesson_id=lesson.id,
                        type=block["type"],
                        content=block["content"],
                        position=position,
                    )
                )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        lock.unlink(missing_ok=True)
        raise CourseImportError("Этот предпросмотр уже был создан.") from error
    lock.unlink(missing_ok=True)
    return course


def _docx_with_headings(path: Path) -> str:
    """DOCX → Markdown с сохранением стилей заголовков для fallback."""
    import zipfile

    from docx import Document

    with zipfile.ZipFile(path) as archive:
        unpacked = sum(item.file_size for item in archive.infolist())
    if unpacked > 50 * 1024 * 1024:
        raise CourseImportError("DOCX распаковывается больше 50 МБ")
    document = Document(str(path))
    if len(document.paragraphs) > 5000:
        raise CourseImportError("В DOCX больше 5000 абзацев")
    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = (paragraph.style.name or "").casefold()
        if "title" in style:
            lines.append(f"# {text}")
        elif "heading 1" in style:
            lines.append(f"## {text}")
        elif "heading 2" in style:
            lines.append(f"### {text}")
        elif "heading" in style:
            lines.append(f"#### {text}")
        else:
            lines.append(text)
    for table in document.tables:
        for row in table.rows:
            lines.append("| " + " | ".join(cell.text for cell in row.cells) + " |")
    return "\n".join(lines)


def extract_file(path: Path) -> str:
    try:
        suffix = ".txt" if path.suffix.lower() == ".md" else path.suffix.lower()
        if suffix == ".docx":
            return _docx_with_headings(path)
        return _extract_text(path, suffix)
    except InterviewError as error:
        raise CourseImportError(str(error)) from error
    except Exception as error:  # noqa: BLE001 — повреждённый PDF/DOCX не должен давать 500
        raise CourseImportError(
            "Не удалось прочитать файл. Проверьте, что PDF/DOCX не повреждён и не защищён паролем."
        ) from error


def delete_preview(token: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{32}", token):
        raise CourseImportError("Некорректный предпросмотр.")
    (_draft_dir() / f"{token}.json").unlink(missing_ok=True)
    (_draft_dir() / f"{token}.lock").unlink(missing_ok=True)
