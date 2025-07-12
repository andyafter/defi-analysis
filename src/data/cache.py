"""Cache implementations for data storage."""

import json
import pickle
import hashlib
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

from ..core.interfaces import ICacheProvider


class FileCache(ICacheProvider):
    """File-based cache implementation."""
    
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        """Initialize file cache.
        
        Args:
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Create hash of key to avoid filesystem issues
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for cache key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)
            
            if not cache_path.exists() or not meta_path.exists():
                self.logger.debug(f"Cache miss for key: {key}")
                return None
            
            try:
                # Check metadata
                with open(meta_path, 'r') as f:
                    metadata = json.load(f)
                
                # Check expiration
                expiry = datetime.fromisoformat(metadata['expiry'])
                if datetime.now() > expiry:
                    self.logger.debug(f"Cache expired for key: {key}")
                    # Clean up expired cache
                    cache_path.unlink(missing_ok=True)
                    meta_path.unlink(missing_ok=True)
                    return None
                
                # Load cached value
                with open(cache_path, 'rb') as f:
                    value = pickle.load(f)
                
                self.logger.debug(f"Cache hit for key: {key}")
                return value
                
            except Exception as e:
                self.logger.error(f"Error reading cache for key {key}: {e}")
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        async with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)
            
            ttl = ttl or self.default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl)
            
            try:
                # Save metadata
                metadata = {
                    'key': key,
                    'created': datetime.now().isoformat(),
                    'expiry': expiry.isoformat(),
                    'ttl': ttl
                }
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f)
                
                # Save value
                with open(cache_path, 'wb') as f:
                    pickle.dump(value, f)
                
                self.logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
                
            except Exception as e:
                self.logger.error(f"Error caching value for key {key}: {e}")
                # Clean up on error
                cache_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
    
    async def delete(self, key: str):
        """Delete value from cache.
        
        Args:
            key: Cache key
        """
        async with self._lock:
            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)
            
            cache_path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            
            self.logger.debug(f"Deleted cache for key: {key}")
    
    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            # Remove all cache files
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)
            
            # Remove all metadata files
            for meta_file in self.cache_dir.glob("*.meta"):
                meta_file.unlink(missing_ok=True)
            
            self.logger.info("Cleared all cache entries")


class CacheKeyBuilder:
    """Helper class to build cache keys."""
    
    @staticmethod
    def pool_state_key(pool_address: str, block_number: int) -> str:
        """Build cache key for pool state."""
        return f"pool_state:{pool_address}:{block_number}"
    
    @staticmethod
    def swap_events_key(pool_address: str, start_block: int, end_block: int) -> str:
        """Build cache key for swap events."""
        return f"swap_events:{pool_address}:{start_block}:{end_block}"
    
    @staticmethod
    def liquidity_distribution_key(
        pool_address: str, 
        block_number: int, 
        tick_lower: int, 
        tick_upper: int
    ) -> str:
        """Build cache key for liquidity distribution."""
        return f"liquidity_dist:{pool_address}:{block_number}:{tick_lower}:{tick_upper}"
    
    @staticmethod
    def block_timestamp_key(block_number: int) -> str:
        """Build cache key for block timestamp."""
        return f"block_timestamp:{block_number}" 