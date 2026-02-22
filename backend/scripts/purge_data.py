import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import get_settings
import psycopg

CLIENT_ID = "9ed16bde-39bd-497e-9996-d0528aa09981"

def main():
    db_url = get_settings().supabase_db_url.replace(":6543", ":5432")
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Disconnect foreign keys safely by deleting dependents first
                cur.execute("DELETE FROM takedowns WHERE threat_id IN (SELECT id FROM threats WHERE client_id = %s);", (CLIENT_ID,))
                cur.execute("DELETE FROM audit_logs WHERE threat_id IN (SELECT id FROM threats WHERE client_id = %s);", (CLIENT_ID,))
                cur.execute("DELETE FROM threats WHERE client_id = %s;", (CLIENT_ID,))
                cur.execute("DELETE FROM assets WHERE client_id = %s;", (CLIENT_ID,))
                conn.commit()
        print("Successfully purged all dirty dummy data for client.")
    except Exception as e:
        print("Purge Failed:", e)

if __name__ == "__main__":
    main()
