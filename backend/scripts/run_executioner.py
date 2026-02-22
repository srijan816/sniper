import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import get_supabase_client
from app.workers.takedown import queue_takedown

CLIENT_ID = "9ed16bde-39bd-497e-9996-d0528aa09981"  # User 'srijan816@gmail.com'
# A benign, actual Shopify store that uses standard Shopify infrastructure
BENIGN_SHOPIFY_URL = "https://www.gymshark.com/products/gymshark-apex-seamless-t-shirt-black-aw21"
ASSET_URL = "https://example.com/asset.jpg"

def main():
    db = get_supabase_client()
    
    # 1. Create Mock Asset
    asset_id = str(uuid.uuid4())
    print("Creating Asset...")
    db.table("assets").insert({
        "id": asset_id,
        "client_id": CLIENT_ID,
        "asset_type": "IMAGE",
        "original_filename": "gymshark_test.jpg",
        "storage_url": ASSET_URL,
        "status": "ACTIVE", # Don't need to actually have real image, just bypass vectorize
    }).execute()
    
    # 2. Inject Threat directly
    threat_id = str(uuid.uuid4())
    print("Creating VERIFIED Threat...")
    db.table("threats").insert({
        "id": threat_id,
        "asset_id": asset_id,
        "client_id": CLIENT_ID,
        "infringing_url": BENIGN_SHOPIFY_URL,
        "host_domain": "www.gymshark.com",
        "similarity_score": 0.99,
        "status": "VERIFIED"
    }).execute()
    
    # 3. Queue Takedown
    takedown_id = str(uuid.uuid4())
    print(f"Creating Takedown Request {takedown_id}...")
    try:
        db.table("takedown_requests").insert({
            "id": takedown_id,
            "threat_id": threat_id,
            "status": "PENDING"
        }).execute()
    except:
        db.table("takedowns").insert({
            "id": takedown_id,
            "threat_id": threat_id,
            "status": "PENDING"
        }).execute()
        
    print("Triggering Celery Takedown Worker...")
    queue_takedown(takedown_id)
    
    print(f"DONE. Monitor Takedown ID: {takedown_id}")

if __name__ == "__main__":
    main()
