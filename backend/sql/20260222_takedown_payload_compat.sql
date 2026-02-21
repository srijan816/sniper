-- SniperIP takedown compatibility migration:
-- Ensure legacy takedowns table supports worker payload updates.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'takedowns'
  ) THEN
    RAISE EXCEPTION 'Required table "takedowns" does not exist.';
  END IF;
END $$;

ALTER TABLE public.takedowns
  ADD COLUMN IF NOT EXISTS rpa_payload jsonb;

