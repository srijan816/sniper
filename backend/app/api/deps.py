from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import get_supabase_client

security = HTTPBearer()

def get_current_client_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    db = get_supabase_client()
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
            
        # 2. Migration: Claim an unowned legacy client (for MVP single-tenant transition)
        legacy_res = db.table("clients").select("id").is_("owner_id", "null").order("created_at").limit(1).execute()
        legacy_rows = legacy_res.data or []
        
        if legacy_rows:
            target_id = legacy_rows[0]["id"]
            db.table("clients").update({"owner_id": owner_id}).eq("id", target_id).execute()
            return target_id
            
        # 3. No client and no legacy? Auto-create a zeroed-out tenant
        import uuid
        new_client_id = str(uuid.uuid4())
        db.table("clients").insert({
            "id": new_client_id,
            "owner_id": owner_id,
            "company_name": user.email,
            "subscription_tier": "FREE",
            "monthly_threat_limit": 1000,
            "current_month_count": 0,
            "whitelist_domains": []
        }).execute()
        return new_client_id
        
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
