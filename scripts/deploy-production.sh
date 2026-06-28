#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/www/wwwroot/project-kizuna.mychisyou.com}"
ENV_BACKUP="/tmp/kizuna-backend.env.bak"

cd "$PROJECT_DIR"

if [ -f backend/.env ]; then
  cp backend/.env "$ENV_BACKUP"
fi

git reset --hard
git clean -fd
git pull

if [ -f "$ENV_BACKUP" ]; then
  cp "$ENV_BACKUP" backend/.env
fi

docker compose down
docker compose up -d --build

docker compose ps
