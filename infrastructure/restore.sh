#!/usr/bin/env sh
# Восстановление production-БД из дампа. Команда destructive:
#   ./infrastructure/restore.sh backups/loadlab-....dump[.gpg]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE=${1:?Укажите путь к .dump или .dump.gpg}
test -s "$FILE"

TMP=$(mktemp "${TMPDIR:-/tmp}/loadlab-restore.XXXXXX")
trap 'rm -f "$TMP"' EXIT HUP INT TERM

if [ "${FILE##*.}" = "gpg" ]; then
  gpg --batch --decrypt --output "$TMP" "$FILE"
else
  cp "$FILE" "$TMP"
fi
test -s "$TMP"

# Не начинаем destructive restore, если файл не похож на дамп.
docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c "pg_restore --list /dev/stdin" < "$TMP" > /dev/null

docker compose -p loadlab-prod -f "$ROOT/infrastructure/docker-compose.prod.yml" \
  exec -T db-prod sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$TMP"
echo "Restored: $FILE"
