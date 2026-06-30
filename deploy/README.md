# Oracle Cloud deployment

Deploy SniperIP on a bare VM (tested target: **140.245.107.78**).

## Quick start (fresh Ubuntu VM)

```bash
# 1. Bootstrap Docker + clone repo
sudo SNIPER_REPO_DIR=/opt/sniper ./scripts/bootstrap-oracle.sh

# 2. Edit secrets
sudo nano /opt/sniper/.env

# 3. Deploy
cd /opt/sniper && sudo ./scripts/deploy-oracle.sh
```

Open `http://140.245.107.78` in a browser.

## Updates after code changes

```bash
cd /opt/sniper
git pull origin cursor/sniperip-pipeline-upgrade-f271
./scripts/deploy-oracle.sh
```

## Architecture

| Service | Role |
|---------|------|
| **caddy** | Reverse proxy :80 → `/api/*` → FastAPI, rest → Next.js |
| **web** | Next.js frontend (standalone) |
| **api** | FastAPI (2 uvicorn workers) |
| **worker-*** | Celery queues: discovery, vectorize, takedown, default |
| **beat** | Celery scheduler (discovery tick, research poll) |
| **redis** | Celery broker + research queue |

## Required `.env` keys

Minimum for startup validation:

- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL`
- `REDIS_URL=redis://redis:6379/0` (pre-set in template)
- `METRICS_AUTH_TOKEN` (any random string for `/api/metrics` scraping)
- `CORS_ORIGINS` must include your public URL

Recommended:

- `SERPAPI_KEY`, `HUGGINGFACE_API_TOKEN`, `RESEND_API_KEY`
- `AIQ_API_TOKEN`, `MINIMAX_API_KEY`

## Oracle Cloud networking

Ensure the VCN security list / NSG allows inbound **TCP 80** and **443** from the internet.

## Safety defaults (Oracle template)

- `TAKEDOWN_TEST_MODE_NO_SUBMIT=true` — no live takedown submissions until verified
- `STRIPE_WEBHOOK_ALLOW_UNSIGNED=false`
- Metrics require bearer token outside development

## Troubleshooting

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api
curl http://127.0.0.1/api/health
cd backend && python scripts/prod_check.py
```

## Domain + HTTPS

1. Point DNS A record to `140.245.107.78`
2. Set `PUBLIC_HOST=yourdomain.com` in `.env`
3. Uncomment the domain block in `deploy/Caddyfile`
4. Redeploy — Caddy will obtain TLS automatically
