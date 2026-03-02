-- Migration: 20260302_pid_features
-- Adds all columns and tables needed for the 8 PID feature set.

-- ── clients table additions ──────────────────────────────────────────────────
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tiktok_bpp_token       text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tiktok_account_email   text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS vero_participant_id    text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS slack_webhook_url      text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS webhook_url            text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS webhook_secret         text;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS average_product_price  numeric(12,2);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS notification_prefs     jsonb DEFAULT '{}'::jsonb;

-- ── threats table additions ──────────────────────────────────────────────────
ALTER TABLE threats ADD COLUMN IF NOT EXISTS registrar          text;
ALTER TABLE threats ADD COLUMN IF NOT EXISTS hosting_provider   text;

-- ── takedowns table additions ────────────────────────────────────────────────
ALTER TABLE takedown_requests ADD COLUMN IF NOT EXISTS completed_at timestamptz;
-- Also add to 'takedowns' alias table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'takedowns') THEN
        ALTER TABLE takedowns ADD COLUMN IF NOT EXISTS completed_at timestamptz;
    END IF;
END $$;

-- ── leads table (PLG free scan) ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email        text NOT NULL,
    ip_address   text,
    image_hash   text,
    matches_found integer DEFAULT 0,
    converted    boolean DEFAULT false,
    converted_at timestamptz,
    created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leads_email      ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);

-- ── authorized_sellers table (whitelist automation) ──────────────────────────
CREATE TABLE IF NOT EXISTS authorized_sellers (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    domain              text NOT NULL,
    seller_name         text,
    platform            text,
    platform_seller_id  text,
    relationship        text NOT NULL DEFAULT 'authorized_distributor'
                            CHECK (relationship IN ('official_retailer','authorized_distributor','licensee','own_property')),
    added_by            text NOT NULL DEFAULT 'manual',
    created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_authorized_sellers_client_id        ON authorized_sellers(client_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_authorized_sellers_client_domain ON authorized_sellers(client_id, domain);
