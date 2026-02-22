import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import get_settings
import psycopg

def main():
    db_url = get_settings().supabase_db_url.replace(":6543", ":5432")
    
    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                # Add the column if it doesn't exist
                cur.execute("""
                    ALTER TABLE threats 
                    ADD COLUMN IF NOT EXISTS ai_explanation TEXT;
                """)
        print("Successfully added ai_explanation column to threats table.")
    except Exception as e:
        print("Migration Failed:", e)

if __name__ == "__main__":
    main()
