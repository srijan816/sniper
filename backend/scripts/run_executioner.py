import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.database import get_supabase_client
from app.workers.takedown import queue_takedown

CLIENT_ID = "9ed16bde-39bd-497e-9996-d0528aa09981"  # User 'srijan816@gmail.com'
# A benign, actual Shopify store that uses standard Shopify infrastructure
BENIGN_SHOPIFY_URL = "https://www.gymshark.com/collections/t-shirts/mens"
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
        "original_filename": "gymshark_apex_seamless_authentic.jpg",
        "storage_url": "https://cdn.shopify.com/s/files/1/0156/6146/products/ApexSeamlessT-ShirtBlackB2A5M-BBBB156_3840x.jpg",
        "status": "ACTIVE",
    }).execute()
    
    # 2. Inject Threat directly
    threat_id = str(uuid.uuid4())
    print("Creating VERIFIED Threat...")
    db.table("threats").insert({
        "id": threat_id,
        "asset_id": asset_id,
        "client_id": CLIENT_ID,
        "infringing_url": BENIGN_SHOPIFY_URL,
        "infringing_image_url": "https://cdn.shopify.com/s/files/1/0156/6146/products/ApexSeamlessT-ShirtBlackB2A5M-BBBB156_3840x.jpg", # Uses similar image for realistic demo
        "host_domain": "www.gymshark.com",
        "similarity_score": 99.1,
        "status": "APPROVED",
        "ai_explanation": "The detected listing image is a 99.1% cosmetic match to the protected asset. Structural similarities include identical pocket placement, exact fabric drape mapping, and replicated collar stitching. The proprietary 'Apex Seamless' geometric knit pattern remains completely intact in the source image structure. The listing price is anomalously low compared to MSRP, strongly corroborating counterfeit status."
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
