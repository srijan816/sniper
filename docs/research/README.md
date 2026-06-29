# Research Pipeline

SniperIP runs **AI-Q deep research sequentially** — one job at a time — to avoid overloading the research API.

## How it works

```
Celery beat (every 120s) ──► research_queue_tick
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Poll active      On complete      Queue empty?
              AI-Q job         save + apply     start next topic
```

## Topics (in order)

1. `vision-ensemble` — SigLIP2/DINOv2 weights, thresholds, deployment
2. `discovery-multisource` — Lens + Bing + Shopping + platform APIs
3. `takedown-automation` — Stagehand vs Playwright, test mode, DMCA

Completed reports land in `docs/research/{topic}.md` via apply hooks.

## Run locally (no Celery)

```bash
cd backend
export AIQ_API_TOKEN=aiq_...
python scripts/research_loop.py --seed          # seed queue
python scripts/research_loop.py                   # poll every 90s
python scripts/research_loop.py --once            # single tick
python scripts/research_loop.py --status          # queue snapshot
```

## Adopt an in-flight job

If research was started manually on AI-Q:

```bash
python scripts/research_loop.py --adopt vision-ensemble <job-id>
```

## Admin API

- `GET /api/admin/research` — queue status
- `POST /api/admin/research/seed` — seed topics
- `POST /api/admin/research/tick` — manual poll
- `POST /api/admin/research/adopt` — `{"topic_key":"...","job_id":"..."}`

## State storage

- **Production:** Redis keys under `sniperip:research:*`
- **Dev/agent fallback:** `backend/.research-queue-state.json`
