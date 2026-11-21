# Резервное копирование и восстановление

## Ежедневно

```bash
./infrastructure/backup.sh /srv/loadlab/backups
```

Скрипт делает `pg_dump -Fc`, проверяет дамп через `pg_restore --list` и хранит
14 дней. Копии нужно дополнительно отправлять в защищённое хранилище вне сервера.

## Восстановление

```bash
./infrastructure/restore.sh /srv/loadlab/backups/loadlab-20261121T120000Z.dump
```

Команда destructive: заменяет текущую БД. Перед восстановлением остановите
backend, чтобы не принимать записи.

## Проверка раз в месяц

1. Взять последнюю копию.
2. Развернуть её в отдельной БД `loadlab_restore_test`.
3. Выполнить `alembic current` и `SELECT count(*) FROM users;`.
4. Убедиться, что backend стартует с этой БД.
5. Удалить тестовую БД.

## Что не входит в дамп

- `.env` и секреты.
- Файлы `uploads/interview` — их нужно копировать отдельно
  (`docker run --rm -v loadlab_prod_interview_uploads:/data ...`).
