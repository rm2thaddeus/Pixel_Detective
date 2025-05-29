# 🚀 Optimized Session State Manager for Pixel Detective
# 📌 Purpose: High-performance session state with background loading
# 🎯 Mission: Eliminate blocking operations and optimize memory usage
# 💡 Based on: Streamlit Background tasks.md research

import streamlit as st
import threading
import time
import logging
from typing import Any, Optional, Dict, Callable
from dataclasses import dataclass
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Thread-safe cache entry with metadata"""
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    is_loading: bool = False
    error: Optional[str] = None


class OptimizedSessionState:
    """
    High-performance session state manager with background loading.
    
    Key features:
    - Thread-safe caching with @st.cache_resource
    - Background loading for heavy operations
    - Smart memory management
    - Performance monitoring
    """
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._background_tasks: Dict[str, threading.Thread] = {}
        
        logger.info("OptimizedSessionState initialized")
    
    def get_or_create(self, key: str, factory: Callable, background: bool = False, timeout: float = 30.0) -> Any:
        """
        Get value from cache or create it using factory function.
        
        Args:
            key: Cache key
            factory: Function to create the value
            background: Whether to load in background
            timeout: Timeout for background loading
        
        Returns:
            The cached or newly created value
        """
        with self._lock:
            # Check if already cached
            if key in self._cache:
                entry = self._cache[key]
                entry.last_accessed = time.time()
                entry.access_count += 1
                
                if entry.error:
                    raise RuntimeError(f"Cached error for {key}: {entry.error}")
                
                if not entry.is_loading:
                    return entry.value
                
                # If loading in background, wait or return placeholder
                if background:
                    return self._wait_for_background_load(key, timeout)
            
            # Not cached, create new entry
            if background:
                return self._start_background_load(key, factory, timeout)
            else:
                return self._load_synchronously(key, factory)
    
    def _load_synchronously(self, key: str, factory: Callable) -> Any:
        """Load value synchronously"""
        start_time = time.time()
        
        try:
            logger.info(f"Loading {key} synchronously...")
            value = factory()
            
            load_time = time.time() - start_time
            logger.info(f"Loaded {key} in {load_time:.2f}s")
            
            # Cache the result
            with self._lock:
                self._cache[key] = CacheEntry(
                    value=value,
                    created_at=start_time,
                    last_accessed=time.time(),
                    access_count=1
                )
            
            return value
            
        except Exception as e:
            error_msg = f"Failed to load {key}: {str(e)}"
            logger.error(error_msg)
            
            # Cache the error
            with self._lock:
                self._cache[key] = CacheEntry(
                    value=None,
                    created_at=start_time,
                    last_accessed=time.time(),
                    error=error_msg
                )
            
            raise RuntimeError(error_msg)
    
    def _start_background_load(self, key: str, factory: Callable, timeout: float) -> Any:
        """Start background loading and return placeholder or wait"""
        with self._lock:
            # Mark as loading
            self._cache[key] = CacheEntry(
                value=None,
                created_at=time.time(),
                last_accessed=time.time(),
                is_loading=True
            )
            
            # Start background thread
            thread = threading.Thread(
                target=self._background_load_worker,
                args=(key, factory),
                daemon=True,
                name=f"Loader-{key}"
            )
            thread.start()
            self._background_tasks[key] = thread
        
        logger.info(f"Started background loading for {key}")
        
        # Wait for completion or timeout
        return self._wait_for_background_load(key, timeout)
    
    def _background_load_worker(self, key: str, factory: Callable):
        """Background worker for loading values"""
        start_time = time.time()
        
        try:
            logger.info(f"Background loading {key}...")
            value = factory()
            
            load_time = time.time() - start_time
            logger.info(f"Background loaded {key} in {load_time:.2f}s")
            
            # Update cache with result
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    entry.value = value
                    entry.is_loading = False
                    entry.error = None
            
        except Exception as e:
            error_msg = f"Background load failed for {key}: {str(e)}"
            logger.error(error_msg)
            
            # Update cache with error
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    entry.is_loading = False
                    entry.error = error_msg
        
        finally:
            # Clean up thread reference
            with self._lock:
                if key in self._background_tasks:
                    del self._background_tasks[key]
    
    def _wait_for_background_load(self, key: str, timeout: float) -> Any:
        """Wait for background loading to complete"""
        start_wait = time.time()
        
        while time.time() - start_wait < timeout:
            with self._lock:
                if key in self._cache:
                    entry = self._cache[key]
                    
                    if entry.error:
                        raise RuntimeError(entry.error)
                    
                    if not entry.is_loading and entry.value is not None:
                        return entry.value
            
            time.sleep(0.1)  # Small sleep to prevent busy waiting
        
        # Timeout reached
        raise TimeoutError(f"Timeout waiting for {key} to load ({timeout}s)")
    
    def is_cached(self, key: str) -> bool:
        """Check if key is cached and ready"""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            return not entry.is_loading and entry.error is None
    
    def is_loading(self, key: str) -> bool:
        """Check if key is currently loading"""
        with self._lock:
            if key not in self._cache:
                return False
            
            return self._cache[key].is_loading
    
    def invalidate(self, key: str):
        """Invalidate a cached entry"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.info(f"Invalidated cache for {key}")
    
    def clear_all(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            logger.info("Cleared all cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            stats = {
                "total_entries": len(self._cache),
                "loading_entries": sum(1 for e in self._cache.values() if e.is_loading),
                "error_entries": sum(1 for e in self._cache.values() if e.error),
                "background_tasks": len(self._background_tasks),
                "entries": {}
            }
            
            for key, entry in self._cache.items():
                stats["entries"][key] = {
                    "created_at": entry.created_at,
                    "last_accessed": entry.last_accessed,
                    "access_count": entry.access_count,
                    "is_loading": entry.is_loading,
                    "has_error": entry.error is not None
                }
            
            return stats


# Global instance with Streamlit caching
@st.cache_resource
def get_optimized_session_state() -> OptimizedSessionState:
    """Get cached optimized session state instance"""
    logger.info("Creating new OptimizedSessionState instance")
    return OptimizedSessionState()


# Convenience functions for common operations
def get_model_manager_optimized():
    """Get model manager with optimized caching"""
    session_state = get_optimized_session_state()
    
    def create_model_manager():
        from core.optimized_model_manager import OptimizedModelManager
        import torch
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        manager = OptimizedModelManager(device)
        
        # Start preloading immediately
        manager.preload_models_async()
        
        return manager
    
    return session_state.get_or_create(
        key="model_manager",
        factory=create_model_manager,
        background=True,
        timeout=60.0
    )


def get_database_manager_optimized():
    """Get database manager with optimized caching"""
    session_state = get_optimized_session_state()
    
    def create_database_manager():
        from database.database_manager import DatabaseManager
        
        # Get the model manager first
        model_manager = get_model_manager_optimized()
        
        # Create database manager
        db_manager = DatabaseManager(model_manager)
        
        return db_manager
    
    return session_state.get_or_create(
        key="database_manager",
        factory=create_database_manager,
        background=True,
        timeout=30.0
    )


# Decorator for automatic caching
def cached_operation(key: str, background: bool = False, timeout: float = 30.0):
    """
    Decorator for automatic caching of expensive operations.
    
    Args:
        key: Cache key
        background: Whether to load in background
        timeout: Timeout for background loading
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            session_state = get_optimized_session_state()
            
            # Create a factory function that calls the original function
            def factory():
                return func(*args, **kwargs)
            
            return session_state.get_or_create(
                key=key,
                factory=factory,
                background=background,
                timeout=timeout
            )
        
        return wrapper
    return decorator


# Example usage functions
@cached_operation("heavy_computation", background=True, timeout=60.0)
def heavy_computation_example():
    """Example of a heavy computation that benefits from caching"""
    import time
    time.sleep(5)  # Simulate heavy work
    return {"result": "computed_value", "timestamp": time.time()}


@cached_operation("model_inference", background=False, timeout=10.0)
def model_inference_example(image_path: str):
    """Example of model inference with caching"""
    # This would use the optimized model manager
    model_manager = get_model_manager_optimized()
    
    # Perform inference
    # result = model_manager.process_image(image_path)
    
    return {"image_path": image_path, "processed": True} 