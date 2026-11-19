# Задание на ревью этапов 10–11 LoadLab

Ревьюер: независимая проверка. Смотри код и поведение, не доверяй отчёту.
Снимок/рабочее дерево содержит этапы 10–11; SAVE_SESSION.md не передаётся.
Статусы этапов — «🟦 реализовано», не «✅ проверено».

## 1. Этап 10. Интерактивные тренажёры

- `GET /trainers/http`, `POST /trainers/http/check` — метод и путь.
- `GET /trainers/sql`, `POST /trainers/sql/run` — только безопасный SELECT,
  ограничение строк, проверка результата.
- `GET /trainers/linux`, `POST /trainers/linux/run` — виртуальная файловая
  система, команды pwd/ls/cat/grep/tail.
- `GET /trainers/analysis`, `POST /trainers/analysis/check` — сценарии анализа.
- Доступ только после входа; ошибки 401/422.
- Frontend `/trainers`: вкладки, формы, результат, состояния ошибок.

Проверить: SQL-инъекции и обход запрета записи, `;`, комментарии, подзапросы,
`pg_*`, `information_schema`, дорогие запросы; утечку данных через SQL; XSS в
выводе; корректность проверки ответов; доступность и 320 px.

## 2. Этап 11. AI Teacher

- `POST /ai/teacher/ask` — вопрос по опубликованному уроку.
- `GET /ai/teacher/history`, `/recommendations`, `/cheatsheet`.
- Локальный режим по материалу урока; опциональный OpenAI-совместимый провайдер
  через `AI_TEACHER_*`, откат при ошибке.
- История в `ai_teacher_messages`; каскады и индексы.
- Frontend: панель в уроке, блок рекомендаций на `/profile/tools`.

Проверить: prompt injection и выход за материал урока; утечку чужих вопросов;
XSS/HTML в ответе; ограничение длины вопроса; поведение без ключа и при таймауте;
не отправляются ли лишние данные; 404 для черновика; доступность; 320 px.

## 3. Команды

```bash
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend alembic check
docker compose exec backend pytest
cd frontend && npm run lint && npm run typecheck && npm run build
```

## 4. Что вернуть

1. Вердикты по этапам 10 и 11 отдельно.
2. P0–P3 с файлами и строками.
3. Что подтверждено выполнением, что статически, что не проверено.
