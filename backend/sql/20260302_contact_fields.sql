-- Migration: add physical contact fields required for 17 U.S.C. § 512(c)(3)(A)(iv)
-- Run against Supabase SQL editor.

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS contact_address text,
  ADD COLUMN IF NOT EXISTS contact_phone   text;

-- Also add the monthly-trend RPC used by Fix 3 in this same migration.
CREATE OR REPLACE FUNCTION get_monthly_threat_trend(p_client_id uuid)
RETURNS TABLE(month text, threat_count bigint, takedown_count bigint)
LANGUAGE sql STABLE AS $$
  SELECT
    to_char(date_trunc('month', t.discovered_at), 'YYYY-MM') AS month,
    count(t.id)                                               AS threat_count,
    count(td.id)                                              AS takedown_count
  FROM threats t
  LEFT JOIN takedowns td
         ON td.threat_id = t.id
        AND td.status IN ('CONFIRMED', 'SUBMITTED', 'COMPLETED')
  WHERE t.client_id = p_client_id
    AND t.discovered_at >= now() - interval '12 months'
  GROUP BY date_trunc('month', t.discovered_at)
  ORDER BY date_trunc('month', t.discovered_at);
$$;
