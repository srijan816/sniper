"""Asset management API routes"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.models.schemas import AssetResponse, AssetType
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter()

# In-memory mock store
_mock_assets = {}


def _seed_demo_assets():
    """Seed demo assets"""
    demos = [
        {
            "id": "asset-demo-001",
            "client_id": "demo-client-001",
            "asset_type": "IMAGE",
            "original_filename": "hero-sneaker-v2.jpg",
            "storage_url": "/storage/assets/hero-sneaker-v2.jpg",
            "thumbnail_url": None,
            "status": "ACTIVE",
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": "asset-demo-002",
            "client_id": "demo-client-001",
            "asset_type": "IMAGE",
            "original_filename": "limited-edition-bag.jpg",
            "storage_url": "/storage/assets/limited-edition-bag.jpg",
            "thumbnail_url": None,
            "status": "ACTIVE",
            "created_at": datetime.now().isoformat(),
        },
        {
            "id": "asset-demo-003",
            "client_id": "demo-client-001",
            "asset_type": "VIDEO",
            "original_filename": "product-360-spin.mp4",
            "storage_url": "/storage/assets/product-360-spin.mp4",
            "thumbnail_url": "/storage/assets/product-360-spin-thumb.jpg",
            "status": "ACTIVE",
            "created_at": datetime.now().isoformat(),
        },
    ]
    for d in demos:
        _mock_assets[d["id"]] = d


_seed_demo_assets()


@router.get("/", response_model=List[AssetResponse])
async def list_assets(client_id: Optional[str] = None):
    """List assets, optionally filtered by client"""
    assets = list(_mock_assets.values())
    if client_id:
        assets = [a for a in assets if a["client_id"] == client_id]
    return assets


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str):
    if asset_id not in _mock_assets:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _mock_assets[asset_id]


@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    client_id: str = Form(...),
    asset_type: str = Form("IMAGE"),
    file: UploadFile = File(...),
):
    """Upload a new asset (image or video)"""
    asset_id = str(uuid.uuid4())
    filename = file.filename or "unknown"

    # In production: upload to Supabase Storage, extract video thumbnail with FFmpeg
    asset = {
        "id": asset_id,
        "client_id": client_id,
        "asset_type": asset_type,
        "original_filename": filename,
        "storage_url": f"/storage/assets/{filename}",
        "thumbnail_url": f"/storage/assets/{filename.rsplit('.', 1)[0]}-thumb.jpg"
        if asset_type == "VIDEO"
        else None,
        "status": "PROCESSING",
        "created_at": datetime.now().isoformat(),
    }
    _mock_assets[asset_id] = asset

    # Trigger async vectorization
    # In production: vectorize_asset_task.delay(asset_id)
    asset["status"] = "ACTIVE"

    return asset


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str):
    if asset_id not in _mock_assets:
        raise HTTPException(status_code=404, detail="Asset not found")
    _mock_assets[asset_id]["status"] = "ARCHIVED"
    return {"status": "archived", "asset_id": asset_id}
