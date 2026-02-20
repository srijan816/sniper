"""Discovery Worker — Module 2: The Radar"""
from datetime import datetime
import uuid
import random

# In production, uncomment:
# from app.celery_app import celery_app
# from app.services.serpapi_service import SerpApiService
# from app.services.resend_service import ResendService


def run_discovery_all():
    """
    Periodic task: Run discovery for all active clients.
    Called by Celery beat every hour.
    """
    # In production:
    # 1. Query all clients with subscription_tier != 'FREE'
    # 2. For each client, check quota: current_month_count < monthly_threat_limit
    # 3. If over quota, send upgrade email via Resend
    # 4. If under quota, run SerpApi query for each client's assets
    # 5. For each result, queue verification task
    pass


def run_discovery_for_client(client_id: str):
    """
    Run discovery for a single client.
    
    Quota Enforcement (from PRD):
    IF clients.current_month_count >= clients.monthly_threat_limit THEN SKIP
    If skipped, trigger Resend email: "You have hit your monthly threat limit."
    """
    # Mock implementation
    # Step 1: Check quota
    # Step 2: Get client's assets
    # Step 3: For each asset, run SerpApi Google Lens search
    # Step 4: For each candidate result, queue verify_threat task
    
    mock_results = [
        {
            "candidate_url": f"https://fake-store-{i}.example.com/product-{random.randint(100,999)}",
            "candidate_image": f"https://via.placeholder.com/400x400",
            "host_domain": f"fake-store-{i}.example.com",
            "seller_name": f"Seller_{random.randint(100,999)}",
            "listing_title": f"Premium Product Clone #{random.randint(1,50)}",
            "listing_price": round(random.uniform(10, 100), 2),
        }
        for i in range(random.randint(0, 5))
    ]
    
    return {
        "client_id": client_id,
        "candidates_found": len(mock_results),
        "results": mock_results,
    }


def check_and_send_quota_warning(client_id: str, current_count: int, limit: int):
    """Send upgrade email when client hits quota"""
    if current_count >= limit:
        # In production: ResendService.send_upgrade_email(client_email)
        return {
            "action": "quota_exceeded",
            "message": "You have hit your monthly threat limit. Upgrade to Growth for continued protection.",
        }
    return {"action": "quota_ok", "remaining": limit - current_count}
