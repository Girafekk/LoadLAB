from app.services.privacy import anonymize


def test_anonymize_contacts_and_name():
    text = "Меня зовут Иван Петров, почта ivan@example.com, телефон +7 999 123-45-67."
    cleaned = anonymize(text)
    assert "Иван" not in cleaned
    assert "ivan@example.com" not in cleaned
    assert "+7 999" not in cleaned
    assert "[имя]" in cleaned
    assert "[email]" in cleaned


def test_anonymize_keeps_technical_text():
    text = "RPS — число запросов в секунду. Пример: 100 RPS."
    assert anonymize(text) == text
