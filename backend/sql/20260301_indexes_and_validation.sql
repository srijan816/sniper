-- Migration: 20260301_indexes_and_validation
-- Adds missing indexes for performance-critical queries and a similarity_score range constraint.

-- threats table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_threats_client_id      ON threats(client_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_threats_status          ON threats(status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_threats_discovered_at   ON threats(discovered_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_threats_asset_id        ON threats(asset_id);

-- audit_logs table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_threat_id    ON audit_logs(threat_id);

-- clients table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_clients_owner_id        ON clients(owner_id);

-- asset_embeddings table
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_asset_embeddings_asset_id ON asset_embeddings(asset_id);

-- similarity_score range constraint (0.0–1.0)
ALTER TABLE threats
    ADD CONSTRAINT chk_similarity_score_range
    CHECK (similarity_score >= 0.0 AND similarity_score <= 1.0)
    NOT VALID;

-- Validate existing rows (runs as a separate pass; does not hold AccessExclusiveLock)
ALTER TABLE threats VALIDATE CONSTRAINT chk_similarity_score_range;
