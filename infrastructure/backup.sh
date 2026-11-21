#!/usr/bin/env sh
# Резервная копия production-БД. Запуск из корня проекта:
#   ./infrastructure/backup.sh [каталог]
# Шифрование (рекомендуется): BACKUP_GPG_RECIPIENT=backup@example.com
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TARGET=${1:-"$ROOT/backups"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
PLAIN="$TARGET/loadlab-$STAMP.dump"
FILE="$PLAIN"
if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  FILE="$PLAIN.gpg"
fi

mkdir -p "$TARGET"
if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
    exec -T db-prod sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    | gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" --output "$FILE"
else
  echo "WARNING: BACKUP_GPG_RECIPIENT не задан — дамп не зашифрован" >&2
  docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
    exec -T db-prod sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"
fi

test -s "$FILE"
if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  gpg --batch --list-packets "$FILE" > /dev/null
else
  docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
    exec -T db-prod sh -c "pg_restore --list /dev/stdin" < "$FILE" > /dev/null
fi

# Храним 14 дней; старые копии удаляем только после успешной проверки.
find "$TARGET" -name 'loadlab-*.dump*' -type f -mtime +14 -delete
echo "Backup: $FILE"
