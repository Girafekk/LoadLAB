# Производительность и нагрузка

## Базовый прогон

1. Поднять production-контур:
   `./infrastructure/deploy.sh`
2. Прогреть: 10 запросов к `/api/v1/health`.
3. Нагрузка JMeter/k6 на `/api/v1/courses/current` и `/api/v1/lessons/1`:
   - 50 виртуальных пользователей;
   - 5 минут;
   - ramp-up 30 секунд.
4. Смотреть p95, p99, RPS, ошибки, CPU/RAM backend и PostgreSQL.

## Ориентиры для учебного проекта

- p95 каталога — до 300 мс при 50 пользователях.
- p95 урока — до 500 мс.
- ошибки 5xx — 0.
- PostgreSQL connections — меньше 80 % лимита.

## Что проверить отдельно

- Пул соединений и `pool_pre_ping`.
- Индексы: `lessons.content_key`, `quiz_attempts(user_id, quiz_id)`,
  `interview_questions.lesson_id`, `interview_question_sources.source_id`.
- Медленные запросы: `pg_stat_statements`.
- Размер загружаемых файлов и OCR: 10 МБ, 30 секунд, отдельный процесс.
- Кэш статики Next.js и gzip в Caddy.

## Результат

Записать в `docs/PERFORMANCE_REPORT.md`: дата, версия снимка, конфигурация,
таблица p50/p95/p99/RPS/errors, узкие места и вывод.
