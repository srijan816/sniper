import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import get_supabase_client

def main():
    db = get_supabase_client()
    # 1. Look up user by email
    # Note: `auth.users` isn't easily queryable via standard REST due to RLS/permissions,
    # but the public `clients` table often contains the user_id or email, or we can insert directly.
    # Let's see if srijan816@gmail.com exists in `clients` or how `client_id` relates.
    res = db.table("clients").select("*").execute().data
    print(f"Found {len(res)} clients.")
    for c in res:
        print(c)

if __name__ == "__main__":
    main()
