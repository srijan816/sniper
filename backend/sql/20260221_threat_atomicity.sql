-- SniperIP hardening migration:
-- 1) Enforce unique pair to prevent race-condition duplicates
-- 2) Add atomic RPC for threat + audit insert

DO $$
DECLARE
  v_duplicate_groups integer := 0;
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'threats'
  ) THEN
    RAISE EXCEPTION 'Required table "threats" does not exist.';
  END IF;

  SELECT COUNT(*)::integer INTO v_duplicate_groups
  FROM (
    SELECT asset_id, infringing_url
    FROM threats
    WHERE asset_id IS NOT NULL AND infringing_url IS NOT NULL
    GROUP BY asset_id, infringing_url
    HAVING COUNT(*) > 1
  ) duplicate_groups;

  IF v_duplicate_groups > 0 THEN
    RAISE EXCEPTION
      'Cannot apply unique index on threats(asset_id, infringing_url): found % duplicate key groups. Resolve duplicates first.',
      v_duplicate_groups;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_threats_asset_infringing_url
  ON threats (asset_id, infringing_url);

CREATE OR REPLACE FUNCTION create_threat_with_audit(
  p_asset_id uuid,
  p_client_id uuid,
  p_infringing_url text,
  p_host_domain text,
  p_similarity_score double precision,
  p_discovered_at timestamptz DEFAULT now()
)
RETURNS TABLE(threat_id uuid, created boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_threat_id uuid;
  v_created boolean := false;
  v_client_id uuid;
BEGIN
  v_client_id := p_client_id;

  IF v_client_id IS NULL THEN
    SELECT client_id INTO v_client_id
    FROM assets
    WHERE id = p_asset_id
    LIMIT 1;
  END IF;

  INSERT INTO threats (
    id,
    asset_id,
    client_id,
    infringing_url,
    host_domain,
    similarity_score,
    status,
    discovered_at
  )
  VALUES (
    extensions.uuid_generate_v4(),
    p_asset_id,
    v_client_id,
    p_infringing_url,
    COALESCE(p_host_domain, ''),
    p_similarity_score,
    'DISCOVERED',
    COALESCE(p_discovered_at, now())
  )
  ON CONFLICT (asset_id, infringing_url)
  DO UPDATE SET
    host_domain = EXCLUDED.host_domain,
    similarity_score = GREATEST(
      COALESCE(threats.similarity_score, 0),
      COALESCE(EXCLUDED.similarity_score, 0)
    )
  RETURNING threats.id, (xmax = 0) INTO v_threat_id, v_created;

  IF v_created THEN
    INSERT INTO audit_logs (
      threat_id,
      old_status,
      new_status,
      changed_by,
      changed_at
    )
    VALUES (
      v_threat_id,
      NULL,
      'DISCOVERED',
      'SYSTEM',
      now()
    );
  END IF;

  RETURN QUERY SELECT v_threat_id, v_created;
END;
$$;

GRANT EXECUTE ON FUNCTION create_threat_with_audit(
  uuid,
  uuid,
  text,
  text,
  double precision,
  timestamptz
) TO service_role;
