#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== MADF Shutdown ==="
docker compose down
echo "=== All services stopped ==="
