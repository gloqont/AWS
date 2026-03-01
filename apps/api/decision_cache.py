"""
GLOQONT Decision Cache — Fast lookup for repeated decisions

This module implements a simple file-based caching layer for decision evaluations.
Cache keys are hashed from decision parameters + portfolio state.

Features:
- File-based JSON cache
- TTL-based expiration (default 1 hour)
- Automatic cache cleanup
"""

import os
import json
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime


# Cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cache")


def _ensure_cache_dir():
    """Ensure cache directory exists."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _generate_cache_key(
    decision_text: str,
    portfolio_id: str,
    horizon_days: int,
    is_fast: bool = False
) -> str:
    """
    Generate a unique cache key for a decision evaluation.
    
    Args:
        decision_text: The original decision text
        portfolio_id: Portfolio identifier
        horizon_days: Simulation horizon
        is_fast: Whether this is a fast approximation
        
    Returns:
        SHA256 hash string
    """
    key_data = f"{decision_text}|{portfolio_id}|{horizon_days}|{is_fast}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


def _get_cache_path(cache_key: str) -> str:
    """Get the file path for a cache key."""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")


def get_cached_result(
    decision_text: str,
    portfolio_id: str,
    horizon_days: int,
    is_fast: bool = False,
    ttl_seconds: int = 3600  # 1 hour default
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a cached decision evaluation result.
    
    Args:
        decision_text: The original decision text
        portfolio_id: Portfolio identifier
        horizon_days: Simulation horizon
        is_fast: Whether this is a fast approximation
        ttl_seconds: Time-to-live for cache entries
        
    Returns:
        Cached result dict or None if not found/expired
    """
    _ensure_cache_dir()
    
    cache_key = _generate_cache_key(decision_text, portfolio_id, horizon_days, is_fast)
    cache_path = _get_cache_path(cache_key)
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        
        # Check TTL
        cached_at = cached.get("cached_at", 0)
        if time.time() - cached_at > ttl_seconds:
            # Expired - remove and return None
            os.remove(cache_path)
            return None
        
        return cached.get("result")
    
    except (json.JSONDecodeError, IOError):
        return None


def set_cached_result(
    decision_text: str,
    portfolio_id: str,
    horizon_days: int,
    result: Dict[str, Any],
    is_fast: bool = False
) -> str:
    """
    Store a decision evaluation result in cache.
    
    Args:
        decision_text: The original decision text
        portfolio_id: Portfolio identifier
        horizon_days: Simulation horizon
        result: The result to cache
        is_fast: Whether this is a fast approximation
        
    Returns:
        Cache key
    """
    _ensure_cache_dir()
    
    cache_key = _generate_cache_key(decision_text, portfolio_id, horizon_days, is_fast)
    cache_path = _get_cache_path(cache_key)
    
    cache_entry = {
        "cached_at": time.time(),
        "decision_text": decision_text,
        "portfolio_id": portfolio_id,
        "horizon_days": horizon_days,
        "is_fast": is_fast,
        "result": result
    }
    
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache_entry, f)
    
    return cache_key


def clear_cache(max_age_seconds: int = 3600):
    """
    Clear expired cache entries.
    
    Args:
        max_age_seconds: Remove entries older than this
    """
    _ensure_cache_dir()
    
    now = time.time()
    removed = 0
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith(".json"):
            continue
        
        filepath = os.path.join(CACHE_DIR, filename)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            cached_at = cached.get("cached_at", 0)
            if now - cached_at > max_age_seconds:
                os.remove(filepath)
                removed += 1
        except (json.JSONDecodeError, IOError):
            # Remove corrupt cache files
            os.remove(filepath)
            removed += 1
    
    return removed


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    _ensure_cache_dir()
    
    total_entries = 0
    total_size = 0
    oldest_entry = None
    newest_entry = None
    
    now = time.time()
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith(".json"):
            continue
        
        filepath = os.path.join(CACHE_DIR, filename)
        total_entries += 1
        total_size += os.path.getsize(filepath)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cached = json.load(f)
            
            cached_at = cached.get("cached_at", 0)
            
            if oldest_entry is None or cached_at < oldest_entry:
                oldest_entry = cached_at
            if newest_entry is None or cached_at > newest_entry:
                newest_entry = cached_at
        except:
            pass
    
    return {
        "total_entries": total_entries,
        "total_size_bytes": total_size,
        "oldest_entry_age_seconds": int(now - oldest_entry) if oldest_entry else None,
        "newest_entry_age_seconds": int(now - newest_entry) if newest_entry else None,
    }


# Example usage
if __name__ == "__main__":
    # Test caching
    print("Testing decision cache...")
    
    # Set a cached result
    test_result = {
        "verdict": "neutral",
        "composite_score": 50.0,
        "summary": "Test decision"
    }
    
    key = set_cached_result(
        decision_text="Buy AAPL 10%",
        portfolio_id="prt_test",
        horizon_days=30,
        result=test_result,
        is_fast=True
    )
    print(f"Cached with key: {key}")
    
    # Retrieve it
    cached = get_cached_result(
        decision_text="Buy AAPL 10%",
        portfolio_id="prt_test",
        horizon_days=30,
        is_fast=True
    )
    print(f"Retrieved: {cached}")
    
    # Get stats
    stats = get_cache_stats()
    print(f"Cache stats: {stats}")
    
    print("Cache test complete!")
