import os
import time

from docx import Document

from app.services import course_import_service as service
from app.services.course_import_service import _docx_with_headings, _local_parse, slugify


def test_docx_headings_and_tables_keep_structure(tmp_path):
    path = tmp_path / "course.docx"
    document = Document()
    document.add_heading("Курс", level=0)
    document.add_heading("Модуль", level=1)
    document.add_heading("Урок", level=2)
    document.add_heading("Теория", level=3)
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Параметр"
    table.rows[0].cells[1].text = "Значение"
    document.save(path)
    text = _docx_with_headings(path)
    assert "## Модуль" in text
    assert "### Урок" in text
    assert "#### Теория" in text
    assert "Параметр" in text and "Значение" in text


def test_cleanup_drafts_removes_old_files(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "_draft_dir", lambda: tmp_path)
    old = tmp_path / "old.json"
    fresh = tmp_path / "fresh.json"
    old.write_text("{}", encoding="utf-8")
    fresh.write_text("{}", encoding="utf-8")
    old_time = time.time() - 25 * 60 * 60
    os.utime(old, (old_time, old_time))
    service.cleanup_drafts()
    assert not old.exists()
    assert fresh.exists()


def test_slugify_transliterates_and_cleans():
    assert slugify("Ручное тестирование") == "ruchnoe-testirovanie"
    assert slugify("  API / v2  ") == "api-v2"
    assert slugify("!!!") == "imported-course"


def test_local_parse_keeps_modules_lessons_and_lists():
    draft = _local_parse(
        "# Курс\n## Модуль 1\n### Урок 1\nТекст урока.\n- пункт\n"
        "## Модуль 2\n### Урок 2\nЕщё текст.",
        "Курс",
    )
    assert [module["title"] for module in draft["modules"]] == ["Модуль 1", "Модуль 2"]
    assert draft["modules"][0]["lessons"][0]["blocks"][0]["type"] == "text"
    assert draft["modules"][0]["lessons"][0]["blocks"][1]["type"] == "list"
