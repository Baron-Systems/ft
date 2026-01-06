"""Caching System - Disk-based caching for translations and extraction results."""

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

try:
    import diskcache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    diskcache = None


class TranslationCache:
    """Disk-based cache for translations and extraction results."""
    
    def __init__(
        self,
        cache_dir: Path,
        lang: Optional[str] = None,
        ttl: int = 86400,  # 24 hours default
    ):
        """
        Initialize translation cache.
        
        Args:
            cache_dir: Cache directory path
            lang: Language code (optional, for language-specific cache)
            ttl: Time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.lang = lang
        self.ttl = ttl
        
        if DISKCACHE_AVAILABLE:
            # Use diskcache if available
            cache_path = self.cache_dir / "translations"
            if lang:
                cache_path = cache_path / lang
            cache_path.mkdir(parents=True, exist_ok=True)
            self.cache = diskcache.Cache(str(cache_path))
        else:
            # Fallback to simple file-based cache
            self.cache = None
            self.cache_path = self.cache_dir / "translations"
            if lang:
                self.cache_path = self.cache_path / lang
            self.cache_path.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if DISKCACHE_AVAILABLE and self.cache:
            try:
                return self.cache.get(key, default=None, expire_time=True)
            except Exception:
                return None
        else:
            # Fallback: file-based cache
            return self._get_file_cache(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional, uses default if not provided)
        """
        if DISKCACHE_AVAILABLE and self.cache:
            try:
                expire = ttl or self.ttl
                self.cache.set(key, value, expire=expire)
            except Exception:
                pass
        else:
            # Fallback: file-based cache
            self._set_file_cache(key, value, ttl or self.ttl)
    
    def delete(self, key: str):
        """Delete key from cache."""
        if DISKCACHE_AVAILABLE and self.cache:
            try:
                self.cache.delete(key)
            except Exception:
                pass
        else:
            # Fallback: file-based cache
            self._delete_file_cache(key)
    
    def clear(self):
        """Clear all cache entries."""
        if DISKCACHE_AVAILABLE and self.cache:
            try:
                self.cache.clear()
            except Exception:
                pass
        else:
            # Fallback: file-based cache
            self._clear_file_cache()
    
    def _get_file_cache(self, key: str) -> Optional[Any]:
        """Get from file-based cache (fallback)."""
        cache_file = self.cache_path / self._key_to_filename(key)
        if not cache_file.exists():
            return None
        
        try:
            import time
            # Check if expired
            if time.time() - cache_file.stat().st_mtime > self.ttl:
                cache_file.unlink()
                return None
            
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data.get("value")
        except Exception:
            return None
    
    def _set_file_cache(self, key: str, value: Any, ttl: int):
        """Set in file-based cache (fallback)."""
        try:
            cache_file = self.cache_path / self._key_to_filename(key)
            data = {"value": value, "ttl": ttl}
            cache_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception:
            pass
    
    def _delete_file_cache(self, key: str):
        """Delete from file-based cache (fallback)."""
        try:
            cache_file = self.cache_path / self._key_to_filename(key)
            if cache_file.exists():
                cache_file.unlink()
        except Exception:
            pass
    
    def _clear_file_cache(self):
        """Clear file-based cache (fallback)."""
        try:
            for cache_file in self.cache_path.glob("*.json"):
                cache_file.unlink()
        except Exception:
            pass
    
    def _key_to_filename(self, key: str) -> str:
        """Convert cache key to filename."""
        # Hash key to avoid filesystem issues
        hash_obj = hashlib.md5(key.encode("utf-8"))
        return f"{hash_obj.hexdigest()}.json"
    
    def get_translation(self, source_text: str, target_lang: str) -> Optional[str]:
        """
        Get cached translation.
        
        Args:
            source_text: Source text
            target_lang: Target language
            
        Returns:
            Cached translation or None
        """
        key = f"translation:{target_lang}:{source_text}"
        return self.get(key)
    
    def set_translation(
        self, source_text: str, target_lang: str, translated_text: str
    ):
        """
        Cache translation.
        
        Args:
            source_text: Source text
            target_lang: Target language
            translated_text: Translated text
        """
        key = f"translation:{target_lang}:{source_text}"
        self.set(key, translated_text)
    
    def get_extraction_result(self, file_path: str) -> Optional[list]:
        """
        Get cached extraction result.
        
        Args:
            file_path: File path
            
        Returns:
            Cached extraction result or None
        """
        key = f"extraction:{file_path}"
        return self.get(key)
    
    def set_extraction_result(self, file_path: str, result: list):
        """
        Cache extraction result.
        
        Args:
            file_path: File path
            result: Extraction result
        """
        key = f"extraction:{file_path}"
        self.set(key, result, ttl=3600)  # 1 hour for extraction results
    
    def get_policy_decision(
        self, text: str, context_hash: str
    ) -> Optional[dict]:
        """
        Get cached policy decision.
        
        Args:
            text: Text
            context_hash: Context hash
            
        Returns:
            Cached decision or None
        """
        key = f"policy:{context_hash}:{text}"
        return self.get(key)
    
    def set_policy_decision(
        self, text: str, context_hash: str, decision: dict
    ):
        """
        Cache policy decision.
        
        Args:
            text: Text
            context_hash: Context hash
            decision: Decision dictionary
        """
        key = f"policy:{context_hash}:{text}"
        self.set(key, decision, ttl=86400 * 7)  # 1 week for policy decisions

