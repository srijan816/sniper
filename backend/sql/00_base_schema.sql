-- =============================================================================
-- SniperIP — Reconstructed BASE schema (00_base_schema.sql)
-- =============================================================================
-- The original Supabase base schema was never committed to the repo; only
-- ALTER/migration files exist under backend/sql/. This file reconstructs the
-- core tables the application code reads/writes so a fresh Postgres can run the
-- app. It is fully idempotent (CREATE ... IF NOT EXISTS everywhere) and is
-- designed to run BEFORE the dated migrations in this directory.
--
-- Every dated migration uses `ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT
-- EXISTS`, so columns/indexes that are also defined here are simply skipped when
-- the migrations run on top. Column TYPES below are matched to the migrations so
-- nothing conflicts.
--
-- IMPORTANT: This file intentionally does NOT define the named CHECK constraint
-- `chk_similarity_score_range` (added by 20260301_indexes_and_validation.sql via
-- a plain `ADD CONSTRAINT`, which is NOT idempotent and would fail if duplicated).
-- =============================================================================

create extension if not exists vector;     -- pgvector (asset_embeddings.embedding)
create extension if not exists pgcrypto;   -- gen_random_uuid()

-- =============================================================================
-- clients
-- Inferred from: app/api/deps.py (owner_id, company_name, subscription_tier,
--   monthly_threat_limit, current_month_count, whitelist_domains insert),
--   app/api/clients.py (_map_client + create/update + analytics + notifications),
--   app/api/webhooks.py / checkout.py (stripe_customer_id, subscription_tier),
--   app/workers/discovery.py (subscription_tier, monthly_threat_limit,
--   current_month_count, whitelist_domains), app/workers/research.py
--   (brand_research). Migration-added columns are mirrored here with matching
--   types (owner_id, loa_document_url, contact_*, tiktok_*, vero_*, webhook_*,
--   average_product_price, notification_prefs, brand_research) so the dated
--   ALTERs remain no-ops.
-- subscription_tier values: FREE | STARTER | GROWTH | AGENCY (app sends strings)
-- =============================================================================
create table if not exists public.clients (
    id                    uuid primary key default gen_random_uuid(),
    -- owner_id: maps tenant -> auth.users(id). 20260223_tenant_isolation.sql adds
    -- this as a bare UUID (no FK), so we keep it FK-free here for portability.
    owner_id              uuid,
    company_name          text,
    legal_contact_name    text,
    legal_contact_email   text,
    subscription_tier     text not null default 'FREE',
    monthly_threat_limit  integer not null default 0,
    current_month_count   integer not null default 0,
    loa_signed_at         timestamptz,
    loa_document_url      text,                 -- 20260222_takedown_payload_compat.sql
    -- whitelist_domains: written as a JSON array (deps.py inserts []); read as a
    -- Python list. jsonb accepts the PostgREST array payload cleanly.
    whitelist_domains     jsonb default '[]'::jsonb,
    stripe_customer_id    text,                 -- webhooks.py / checkout.py (no migration defines it)
    contact_address       text,                 -- 20260302_contact_fields.sql
    contact_phone         text,                 -- 20260302_contact_fields.sql
    tiktok_bpp_token      text,                 -- 20260302_pid_features.sql
    tiktok_account_email  text,                 -- 20260302_pid_features.sql
    vero_participant_id   text,                 -- 20260302_pid_features.sql
    slack_webhook_url     text,                 -- 20260302_pid_features.sql
    webhook_url           text,                 -- 20260302_pid_features.sql
    webhook_secret        text,                 -- 20260302_pid_features.sql
    average_product_price numeric(12,2),        -- 20260302_pid_features.sql
    notification_prefs    jsonb default '{}'::jsonb,  -- 20260302_pid_features.sql
    brand_research        jsonb,                -- 20260629_brand_research.sql
    created_at            timestamptz not null default now()
);

create index if not exists idx_clients_owner_id ON public.clients(owner_id);

-- =============================================================================
-- assets
-- Inferred from: app/api/assets.py (_map_asset + upload insert), app/api/verify.py
--   (select id,original_filename,storage_url,thumbnail_url,asset_type),
--   app/workers/vectorize.py (storage_url, asset_type, thumbnail_url update),
--   app/workers/discovery.py (status='ACTIVE' filter).
-- asset_type values: IMAGE | VIDEO    status values: ACTIVE | ARCHIVED
-- =============================================================================
create table if not exists public.assets (
    id                 uuid primary key default gen_random_uuid(),
    client_id          uuid references public.clients(id) on delete cascade,
    asset_type         text not null default 'IMAGE',
    original_filename  text,
    storage_url        text,
    thumbnail_url      text,
    status             text not null default 'ACTIVE',
    created_at         timestamptz not null default now()
);

create index if not exists idx_assets_client_id ON public.assets(client_id);

-- =============================================================================
-- threats
-- Inferred from: create_threat_with_audit() in 20260221_threat_atomicity.sql
--   (id, asset_id, client_id, infringing_url, host_domain, similarity_score,
--   status, discovered_at + ON CONFLICT (asset_id, infringing_url)),
--   app/api/threats.py _map_threat (infringing_image_url, seller_name,
--   listing_title, listing_price, ai_explanation, resolved_at),
--   app/models/schemas.py ThreatResponse, 20260302_pid_features.sql
--   (registrar, hosting_provider), 20260301_indexes_and_validation.sql
--   (indexes on client_id, status, discovered_at, asset_id).
-- similarity_score is double precision (matches RPC param). The 0.0–1.0 CHECK is
--   added by 20260301 (NOT idempotent) and is deliberately omitted here.
-- status values: DISCOVERED | PENDING_APPROVAL | APPROVED | WHITELISTED |
--   REJECTED | TAKEDOWN_SUBMITTED | TAKEDOWN_CONFIRMED | REMOVED
-- =============================================================================
create table if not exists public.threats (
    id                    uuid primary key default gen_random_uuid(),
    asset_id              uuid references public.assets(id) on delete cascade,
    client_id             uuid references public.clients(id) on delete cascade,
    infringing_url        text,
    infringing_image_url  text,
    host_domain           text not null default '',
    seller_name           text,
    listing_title         text,
    listing_price         double precision,
    similarity_score      double precision,
    ai_explanation        text,
    status                text not null default 'DISCOVERED',
    registrar             text,                 -- 20260302_pid_features.sql
    hosting_provider      text,                 -- 20260302_pid_features.sql
    discovered_at         timestamptz not null default now(),
    resolved_at           timestamptz
);

-- Unique pair prevents race-condition duplicates and backs the RPC's
-- ON CONFLICT (asset_id, infringing_url). Same name as 20260221 (IF NOT EXISTS).
create unique index if not exists uq_threats_asset_infringing_url
    ON public.threats(asset_id, infringing_url);

-- Same names as 20260301_indexes_and_validation.sql (created CONCURRENTLY there;
-- IF NOT EXISTS means they are skipped once these plain ones exist).
create index if not exists idx_threats_client_id    ON public.threats(client_id);
create index if not exists idx_threats_status         ON public.threats(status);
create index if not exists idx_threats_discovered_at  ON public.threats(discovered_at DESC);
create index if not exists idx_threats_asset_id       ON public.threats(asset_id);

-- =============================================================================
-- audit_logs
-- Inferred from: create_threat_with_audit() in 20260221_threat_atomicity.sql
--   (threat_id, old_status, new_status, changed_by, changed_at),
--   app/api/threats.py + app/workers/{takedown,monitoring}.py inserts (no id
--   supplied -> needs default), ordered/filtered by threat_id and changed_at.
-- `metadata` is present in AuditLogResponse but never written/read from the DB;
--   included as nullable jsonb for forward-compatibility (see UNCERTAIN note).
-- =============================================================================
create table if not exists public.audit_logs (
    id          uuid primary key default gen_random_uuid(),
    threat_id   uuid references public.threats(id) on delete cascade,
    old_status  text,
    new_status  text,
    changed_by  text not null default 'SYSTEM',
    metadata    jsonb default '{}'::jsonb,
    changed_at  timestamptz not null default now()
);

create index if not exists idx_audit_logs_threat_id ON public.audit_logs(threat_id);

-- =============================================================================
-- takedowns  (legacy/alias table)
-- Inferred from: app/api/takedown.py _map_takedown + submit insert, app/api/
--   threats.py approve insert, app/workers/takedown.py updates, app/api/clients.py
--   analytics select (status, completed_at, platform). Migrations:
--   20260222 adds rpa_payload; 20260302_pid_features adds completed_at.
-- NOTE: the code prefers a `takedown_requests` table and falls back to
--   `takedowns`. See takedown_requests below.
-- status values: PENDING | SUBMITTED | CONFIRMED | FAILED | REINSTATED
-- =============================================================================
create table if not exists public.takedowns (
    id            uuid primary key default gen_random_uuid(),
    threat_id     uuid references public.threats(id) on delete cascade,
    platform      text,
    case_number   text,
    status        text not null default 'PENDING',
    retry_count   integer not null default 0,
    rpa_payload   jsonb,                -- 20260222_takedown_payload_compat.sql
    submitted_at  timestamptz,
    completed_at  timestamptz,          -- 20260302_pid_features.sql
    created_at    timestamptz not null default now()
);

create index if not exists idx_takedowns_threat_id ON public.takedowns(threat_id);

-- =============================================================================
-- takedown_requests  (PRIMARY takedown table — code tries this name first)
-- NOT in the original 8-table list, but the code in app/api/{takedown,threats}.py,
--   app/workers/{takedown,monitoring}.py and app/api/admin.py all try
--   "takedown_requests" before "takedowns", and 20260302_pid_features.sql does an
--   unconditional `ALTER TABLE takedown_requests ADD COLUMN IF NOT EXISTS
--   completed_at` (which would fail if the table were absent). Created with the
--   same shape as `takedowns` so either path works.
-- =============================================================================
create table if not exists public.takedown_requests (
    id            uuid primary key default gen_random_uuid(),
    threat_id     uuid references public.threats(id) on delete cascade,
    platform      text,
    case_number   text,
    status        text not null default 'PENDING',
    retry_count   integer not null default 0,
    rpa_payload   jsonb,
    submitted_at  timestamptz,
    completed_at  timestamptz,
    created_at    timestamptz not null default now()
);

create index if not exists idx_takedown_requests_threat_id ON public.takedown_requests(threat_id);

-- =============================================================================
-- dead_letter_queue  (failed takedown sink)
-- NOT in the original 8-table list, but required by app/workers/takedown.py
--   (_insert_dlq) and app/api/admin.py (DLQ endpoints + _map_dlq). Code tries
--   "dead_letter_queue" then "dlq".
-- =============================================================================
create table if not exists public.dead_letter_queue (
    id            uuid primary key default gen_random_uuid(),
    takedown_id   uuid,
    error_reason  text,
    failed_at     timestamptz not null default now()
);

create index if not exists idx_dead_letter_queue_failed_at ON public.dead_letter_queue(failed_at DESC);

-- =============================================================================
-- cost_metrics  (telemetry, read-only in app)
-- Inferred from: app/api/admin.py get_cost_metrics — select * order by created_at
--   desc; reads serpapi_credits_used, serpapi_credits_limit, hf_compute_hours,
--   zenrows_bandwidth_mb. No insert path exists in the codebase.
-- =============================================================================
create table if not exists public.cost_metrics (
    id                    uuid primary key default gen_random_uuid(),
    serpapi_credits_used  integer default 0,
    serpapi_credits_limit integer default 10000,
    hf_compute_hours      double precision default 0.0,
    zenrows_bandwidth_mb  double precision default 0.0,
    created_at            timestamptz not null default now()
);

create index if not exists idx_cost_metrics_created_at ON public.cost_metrics(created_at DESC);

-- =============================================================================
-- bad_actor_signals
-- Inferred from: app/api/clients.py analytics — only `select("id", count="exact")`
--   is ever issued, so ONLY the `id` column is evidenced. The remaining columns
--   below mirror the BadActorSignals dataclass + the runtime `blacklist_actors`
--   table (app/services/blacklist_store.py) as the most plausible shape.
-- UNCERTAIN: see summary — non-`id` columns are a best-effort reconstruction.
-- =============================================================================
create table if not exists public.bad_actor_signals (
    id                  uuid primary key default gen_random_uuid(),
    host_domain         text,
    seller_name         text,
    support_email       text,
    payment_gateway_id  text,
    threat_count        integer not null default 1,
    first_seen_at       timestamptz not null default now(),
    last_seen_at        timestamptz not null default now()
);

-- =============================================================================
-- asset_embeddings  (pgvector store)
-- Inferred from: app/services/vector_store.py raw SQL — INSERT (id, asset_id,
--   phash, embedding::vector), SELECT embedding::text / phash, cosine search
--   (embedding <=> ...). 20260301 adds idx_asset_embeddings_asset_id;
--   20260630_pgvector_hnsw.sql adds the HNSW cosine index (left to that
--   migration to avoid duplicating the build-time index here).
-- Vector dimension = 1152 (see summary): app/core/config.py embedding_dimension
--   default 1152 for google/siglip-so400m-patch14-384, confirmed by the
--   20260630 migration comment.
-- =============================================================================
create table if not exists public.asset_embeddings (
    id          uuid primary key default gen_random_uuid(),
    asset_id    uuid references public.assets(id) on delete cascade,
    phash       text,
    embedding   vector(1152),
    created_at  timestamptz not null default now()
);

-- Same name as 20260301_indexes_and_validation.sql (IF NOT EXISTS).
create index if not exists idx_asset_embeddings_asset_id ON public.asset_embeddings(asset_id);
