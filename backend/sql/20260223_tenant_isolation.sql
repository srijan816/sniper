-- Migration to enforce Tenant Isolation & IDOR Protection
ALTER TABLE clients ADD COLUMN IF NOT EXISTS owner_id UUID;
