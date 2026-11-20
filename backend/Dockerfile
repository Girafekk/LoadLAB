# Образ backend LoadLab на Python 3.12.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OCR для скриншотов вопросов: английский и русский языки.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# Сначала копируем только списки зависимостей: пока они не меняются,
# Docker берёт установленные пакеты из кэша и сборка идёт быстро.
COPY requirements.txt requirements-dev.txt ./

# INSTALL_DEV=true добавляет инструменты разработки (pytest, ruff).
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install -r requirements-dev.txt; \
    else \
        pip install -r requirements.txt; \
    fi

COPY . .

# Приложение работает от обычного пользователя, а не от root.
RUN useradd --create-home --uid 1000 loadlab \
    && mkdir -p /app/uploads/interview \
    && chown -R loadlab:loadlab /app/uploads
USER loadlab

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
