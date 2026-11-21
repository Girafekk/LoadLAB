# Безопасность LoadLab

## Обязательные проверки перед публикацией

- [ ] `.env` не в Git; в репозитории только `.env.example` без секретов.
- [ ] `DEEPSEEK_API_KEY` и токены AI заданы только в окружении сервера.
- [ ] `POSTGRES_PASSWORD` и `PROD_POSTGRES_PASSWORD` разные и длинные.
- [ ] `ENVIRONMENT=production`; cookie сессии `Secure`, `HttpOnly`, `SameSite=Lax`.
- [ ] `CORS_ORIGINS` содержит только реальные адреса фронтенда.
- [ ] HTTPS-сертификат валиден; HTTP перенаправляется на HTTPS.
- [ ] Порт PostgreSQL не опубликован наружу.
- [ ] Резервные копии шифруются и хранятся вне сервера.
- [ ] `pip-audit -r backend/requirements.txt` без critical/high.
- [ ] `npm audit --omit=dev --audit-level=high` в `frontend/` без critical/high.
- [ ] Проверены роли: ученик не получает 200 на `/api/v1/admin/*`.
- [ ] Проверен чужой ресурс: 404, а не чужие данные.
- [ ] Загрузка ограничена 10 МБ и типом файла.
- [ ] SQL-тренажёр не читает `users`/`sessions` и не пишет в БД.
- [ ] Внешний AI выключен по умолчанию; согласие администратора явное.

## Что не хранить в репозитории

Пароли, JWT/API-ключи, `.env`, дампы БД, real interview materials,
`node_modules`, `.next`, `__pycache__`, локальные `*.db`.

## Реакция на инцидент

1. Отозвать ключ/пароль, сменить `POSTGRES_PASSWORD`.
2. Остановить backend: `docker compose -p loadlab-prod stop backend-prod`.
3. Сохранить логи и дамп для разбора.
4. Восстановить БД из последней проверенной копии при потере данных.
5. После исправления — новый снимок и повторный security-check.
