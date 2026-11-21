#!/usr/bin/env sh
# Резервная копия production-БД. Запуск из корня проекта:
#   ./infrastructure/backup.sh [каталог]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TARGET=${1:-"$ROOT/backups"}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
FILE="$TARGET/loadlab-$STAMP.dump"

mkdir -p "$TARGET"
docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$FILE"

# Проверяем, что дамп читается и не пустой.
test -s "$FILE"
docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c "pg_restore --list /dev/stdin" < "$FILE" > /dev/null

# Храним 14 дней; старые копии удаляем только после успешной проверки.
find "$TARGET" -name 'loadlab-*.dump' -type f -mtime +14 -delete
echo "Backup: $FILE"
