"""Vectorization Worker — SigLIP 2 + pHash"""
import uuid
import random
import hashlib


def vectorize_asset(asset_id: str, image_url: str):
    """
    Vectorize an image asset:
    1. Download the image from storage_url
    2. Generate SigLIP 2 embedding (768-dim vector)
    3. Compute pHash for fast dedup
    4. Store in asset_embeddings table
    
    In production, uses:
    - transformers (SigLIP 2 model)
    - imagehash (pHash)
    - Supabase client for DB writes
    """
    # Mock implementation
    mock_embedding = [random.uniform(-1, 1) for _ in range(768)]
    mock_phash = hashlib.md5(f"phash-{asset_id}".encode()).hexdigest()[:16]
    
    return {
        "asset_id": asset_id,
        "phash": mock_phash,
        "embedding_dim": len(mock_embedding),
        "status": "vectorized",
    }


def extract_video_frame(video_url: str, timestamp: float = 3.0):
    """
    Extract a frame from a video at the given timestamp.
    
    Uses ffmpeg-python:
    ffmpeg.input(video_url, ss=timestamp).output(output_path, vframes=1).run()
    
    Returns the path to the extracted thumbnail.
    """
    # Mock: return a placeholder thumbnail path
    frame_filename = f"frame_{int(timestamp*1000)}ms.jpg"
    return {
        "thumbnail_path": f"/tmp/sniperip/frames/{frame_filename}",
        "timestamp": timestamp,
        "status": "extracted",
    }


def compute_similarity(embedding_a: list, embedding_b: list) -> float:
    """
    Compute cosine similarity between two SigLIP embeddings.
    Score >= 0.95 → confirmed threat.
    """
    # Mock: return random similarity
    return round(random.uniform(0.88, 0.99), 4)
