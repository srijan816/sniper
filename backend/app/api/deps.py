import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import get_settings
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

security = HTTPBearer()


def get_current_client_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured.")
    try:
        token = credentials.credentials
        user_res = db.auth.get_user(token)
        user = user_res.user
        if not user:
            raise ValueError("Invalid session")

        owner_id = user.id

        # 1. Lookup existing client mapping
        client_res = db.table("clients").select("id").eq("owner_id", owner_id).limit(1).execute()
        rows = client_res.data or []

        if rows:
            return rows[0]["id"]

        # 2. Migration: Claim an unowned legacy client atomically using a single UPDATE RETURNING
        # to avoid a SELECT-then-UPDATE race condition where two users claim the same client.
        try:
            from app.core.database import get_pg_connection
            with get_pg_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE clients
                        SET owner_id = %s
                        WHERE id = (
                            SELECT id FROM clients
                            WHERE owner_id IS NULL
                            ORDER BY created_at
                            LIMIT 1
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING id
                        """,
                        (owner_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return str(row[0])
        except Exception as exc:
            logger.warning("Atomic legacy client claim failed, falling through to auto-create: %s", exc)

        # 3. No client and no legacy? Auto-create a zeroed-out tenant
        import uuid
        new_client_id = str(uuid.uuid4())
        db.table("clients").insert({
            "id": new_client_id,
            "owner_id": owner_id,
            "company_name": user.email or "New Client",
            "legal_contact_name": (user.email or "New Client").split("@")[0][:120] or "New Client",
            "legal_contact_email": user.email or f"{new_client_id}@example.invalid",
            "subscription_tier": "FREE",
            "monthly_threat_limit": 1000,
            "current_month_count": 0,
            "whitelist_domains": []
        }).execute()
        return new_client_id

    except Exception as exc:
        logger.error("Authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency that verifies the authenticated user is a configured admin."""
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase is not configured.")
    try:
        token = credentials.credentials
        user_res = db.auth.get_user(token)
        user = user_res.user
        if not user:
            raise ValueError("Invalid session")

        user_email = (user.email or "").lower().strip()
        if not user_email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        settings = get_settings()
        raw_admin_emails = os.environ.get("ADMIN_EMAILS") or settings.admin_emails or ""
        admin_emails = {e.strip().lower() for e in raw_admin_emails.split(",") if e.strip()}
        if user_email not in admin_emails:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Return the client_id associated with this admin user (may be None for superadmin with no client)
        owner_id = user.id
        client_res = db.table("clients").select("id").eq("owner_id", owner_id).limit(1).execute()
        rows = client_res.data or []
        return rows[0]["id"] if rows else owner_id

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Admin authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
