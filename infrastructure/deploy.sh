#!/usr/bin/env sh
# Сборка и запуск production-контура. Запуск из корня проекта.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml build
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml up -d --remove-orphans

# Миграции и стартовый контент: на пустой БД health без них покажет
# database=unavailable, а каталог вернёт 404.
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml \
  exec -T backend-prod alembic upgrade head
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml \
  exec -T backend-prod python -m app.db.seed
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml \
  exec -T backend-prod python -m app.db.content_loader --publish-new

# Ждём healthcheck backend и проверяем, что API отвечает через прокси.
for _ in $(seq 1 30); do
  if curl -fsSk https://localhost:8443/api/v1/health > /dev/null 2>&1; then
    echo "LoadLab production is up: https://localhost:8443"
    exit 0
  fi
  sleep 2
done
echo "Backend не ответил за 60 секунд" >&2
docker compose -p loadlab-prod -f infrastructure/docker-compose.prod.yml logs --tail=80 backend-prod >&2
exit 1
