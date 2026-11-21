#!/usr/bin/env sh
# Восстановление production-БД из дампа. Команда destructive:
#   ./infrastructure/restore.sh backups/loadlab-....dump[.gpg]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE=${1:?Укажите путь к .dump или .dump.gpg}
test -s "$FILE"

if [ "${FILE##*.}" = "gpg" ]; then
  gpg --batch --decrypt "$FILE" | docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
    exec -T db-prod sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
else
  docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
    exec -T db-prod sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$FILE"
fi
echo "Restored: $FILE"
