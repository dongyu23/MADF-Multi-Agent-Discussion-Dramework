#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== MADF Startup ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: docker compose not found"; exit 1; }

# Build and start all services
echo "[1/3] Building images..."
docker compose build --quiet

echo "[2/3] Starting services..."
docker compose up -d

echo "[3/3] Waiting for backend health check..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        echo ""
        echo "=== MADF is ready ==="
        echo "  Frontend: http://localhost"
        echo "  Backend:  http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        exit 0
    fi
    printf "."
    sleep 2
done

echo ""
echo "WARNING: Backend did not become healthy within 60s."
echo "Check logs: docker compose logs backend"
exit 1
