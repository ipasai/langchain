#!/usr/bin/env bash
set -euo pipefail

# Simple docker-compose based deploy helper
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

if [[ ${1:-} == "down" ]]; then
  docker compose down
  exit 0
fi

docker compose pull || true
docker compose build --pull
docker compose up -d --remove-orphans
echo "Services started. To view logs: docker compose logs -f"
