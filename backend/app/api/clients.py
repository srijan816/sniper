"""Client API routes"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ClientCreate, ClientResponse, ClientAnalytics
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

# In-memory mock store for development
_mock_clients = {}


def _seed_demo_client():
    """Create a demo client for development"""
    demo_id = "demo-client-001"
    if demo_id not in _mock_clients:
        _mock_clients[demo_id] = {
            "id": demo_id,
            "user_id": "demo-user-001",
            "company_name": "Demo Brand Co.",
            "legal_contact_name": "Jane Doe",
            "legal_contact_email": "jane@demobrand.com",
            "subscription_tier": "GROWTH",
            "monthly_threat_limit": 500,
            "current_month_count": 47,
            "loa_signed_at": datetime.now().isoformat(),
            "whitelist_domains": ["demobrand.com", "demobrand.co.uk"],
            "stripe_customer_id": "cus_demo_001",
            "is_admin": False,
            "created_at": datetime.now().isoformat(),
        }


_seed_demo_client()


@router.get("/", response_model=List[ClientResponse])
async def list_clients():
    """List all clients (admin only in production)"""
    return list(_mock_clients.values())


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str):
    """Get a client by ID"""
    if client_id not in _mock_clients:
        raise HTTPException(status_code=404, detail="Client not found")
    return _mock_clients[client_id]


@router.post("/", response_model=ClientResponse)
async def create_client(data: ClientCreate):
    """Register a new client"""
    client_id = str(uuid.uuid4())
    client = {
        "id": client_id,
        "user_id": str(uuid.uuid4()),
        **data.model_dump(),
        "subscription_tier": "FREE",
        "monthly_threat_limit": 0,
        "current_month_count": 0,
        "loa_signed_at": None,
        "whitelist_domains": [],
        "stripe_customer_id": None,
        "is_admin": False,
        "created_at": datetime.now().isoformat(),
    }
    _mock_clients[client_id] = client
    return client


@router.get("/{client_id}/analytics", response_model=ClientAnalytics)
async def get_client_analytics(client_id: str):
    """Get ROI analytics for a client"""
    if client_id not in _mock_clients:
        raise HTTPException(status_code=404, detail="Client not found")

    # Mock analytics data
    return ClientAnalytics(
        threats_found_this_month=47,
        threats_removed_this_month=38,
        estimated_revenue_protected=28400.00,
        average_order_value=747.37,
    )
