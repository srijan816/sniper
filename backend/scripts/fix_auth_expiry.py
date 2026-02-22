import os
import sys
import psycopg
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import get_settings

def print_auth_schema():
    db_url = get_settings().supabase_db_url.replace(":6543", ":5432")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # 1. Print all auth tables
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'auth'")
                tables = [t[0] for t in cur.fetchall()]
                print("Auth Tables:", tables)
                
                # 2. Check if auth.config exists (it rarely does in managed Supabase, usually it's env vars)
                if 'config' in tables:
                    print("Auth config table found. Let's inspect it.")
                else:
                    print("No auth.config table found. We may need to use the UI or Management API.")
                    
                # 3. Check auth.flow_state columns to see if there's an expiry we can patch temporarily
                if 'flow_state' in tables:
                    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'auth' AND table_name = 'flow_state'")
                    cols = [c[0] for c in cur.fetchall()]
                    print("auth.flow_state columns:", cols)
                    
    except Exception as e:
        print("Database Error:", e)

if __name__ == "__main__":
    print_auth_schema()
