#!/usr/bin/env sh
# Восстановление production-БД из дампа. Команда destructive:
#   ./infrastructure/restore.sh backups/loadlab-....dump
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE=${1:?Укажите путь к .dump}
test -s "$FILE"

docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$FILE"
echo "Restored: $FILE"
