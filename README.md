# SniperIP

Automated IP protection SaaS for D2C brands.

This repository now contains **both frontend and backend**:

- `src/`, `public/`, `next.config.ts`: Next.js application (marketing site + app UI)
- `backend/`: FastAPI + Celery backend workers

## Stack

- Frontend: Next.js, Tailwind CSS, React
- Backend: FastAPI, Celery, Redis, Supabase client
- Infra: Stripe, Resend, Playwright, HuggingFace (via backend integrations)

## Local Development

### 1) Frontend

```bash
npm install
npm run dev
```

Runs on `http://localhost:3000`.

### 2) Backend API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Runs on `http://localhost:8000`.

### 3) Celery Worker

```bash
cd backend
source .venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

## Environment

Copy `.env.example` to `.env` and fill required values.

```bash
cp .env.example .env
```

For hardened verification/RPA, set:
- `HUGGINGFACE_EMBEDDING_BACKEND=local` (or `endpoint`)
- Meta/Amazon/Playwright proxy env vars when those integrations are enabled

## Database Migration

Apply the hardening SQL before enabling workers:

```bash
psql "$SUPABASE_DB_URL" -f backend/sql/20260221_threat_atomicity.sql
```

## Notes

- Marketing routes live under `/` and `/pricing`.
- Application routes live under `/dashboard` and `/admin`.
- Backend source is in `backend/app`.
