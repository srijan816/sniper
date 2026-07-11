-- Brand research cache from AI-Q deep research (optional column)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS brand_research JSONB;
