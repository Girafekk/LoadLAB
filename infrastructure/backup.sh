#!/usr/bin/env sh
# Резервная копия production-БД. Запуск из корня проекта:
#   ./infrastructure/backup.sh [каталог]
# Шифрование: BACKUP_GPG_RECIPIENT=backup@example.com
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
TMP="$PLAIN.tmp"
trap 'rm -f "$TMP"' EXIT HUP INT TERM

# Сначала целиком получаем дамп: если pg_dump упадёт, файла не будет.
docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$TMP"
test -s "$TMP"

# Проверяем именно дамп, а не только оболочку контейнера.
docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c "pg_restore --list /dev/stdin" < "$TMP" > /dev/null

if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" \
    --output "$FILE" "$TMP"
  gpg --batch --list-packets "$FILE" > /dev/null
  rm -f "$TMP"
else
  echo "WARNING: BACKUP_GPG_RECIPIENT не задан — дамп не зашифрован" >&2
  mv "$TMP" "$FILE"
fi

# Храним 14 дней; старые копии удаляем только после успешной проверки.
find "$TARGET" -name 'loadlab-*.dump*' -type f -mtime +14 -delete
echo "Backup: $FILE"
