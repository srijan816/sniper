#!/usr/bin/env bash
# Pull latest code and restart the production stack.
# Usage (on Oracle server):
#   cd /opt/sniper && ./scripts/deploy-oracle.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BRANCH="${SNIPER_BRANCH:-cursor/sniperip-pipeline-upgrade-f271}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

echo "==> SniperIP deploy from $(pwd) (branch: ${BRANCH})"

if [[ ! -f .env ]]; then
  if [[ -f deploy/env.oracle.example ]]; then
    cp deploy/env.oracle.example .env
  fi
  echo "ERROR: .env missing or just created from template."
  echo "Edit .env with your Supabase/Stripe/API keys, then re-run this script."
  exit 1
fi

if grep -q 'CHANGE_ME' .env 2>/dev/null; then
  echo "ERROR: .env still contains CHANGE_ME placeholders. Fill in secrets first."
  exit 1
fi

if [[ -z "${SUPABASE_URL:-}" ]] && ! grep -q '^SUPABASE_URL=' .env; then
  echo "ERROR: SUPABASE_URL not set in .env"
  exit 1
fi

echo "==> Git pull..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> Pre-deploy check..."
docker compose -f "$COMPOSE_FILE" run --rm --no-deps api python scripts/prod_check.py || {
  echo "WARN: prod_check reported issues — continuing if containers can start."
}

echo "==> Building images..."
docker compose -f "$COMPOSE_FILE" build --pull

echo "==> Starting stack..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "==> Waiting for health..."
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1/api/health" >/dev/null 2>&1; then
    echo "API healthy."
    break
  fi
  if [[ "$i" -eq 30 ]]; then
    echo "ERROR: API did not become healthy in time."
    docker compose -f "$COMPOSE_FILE" ps
    docker compose -f "$COMPOSE_FILE" logs --tail=50 api
    exit 1
  fi
  sleep 2
done

echo ""
echo "==> Deploy complete"
docker compose -f "$COMPOSE_FILE" ps
echo ""
echo "App URL:  ${NEXT_PUBLIC_APP_URL:-http://140.245.107.78}"
echo "API health: http://127.0.0.1/api/health"
curl -fsS "http://127.0.0.1/api/health" | head -c 400 || true
echo ""
