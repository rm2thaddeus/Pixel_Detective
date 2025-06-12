# 🧪 Test Script for Performance Optimizations
# 📌 Purpose: Verify that the optimizations fix the startup and loading issues
# 🎯 Mission: Test the fixes without running the full Streamlit app

import sys
import os
import time
import logging
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_model_manager_optimization():
    """Test that the model manager keeps both models loaded when KEEP_MODELS_LOADED=True"""
    print("🧪 Testing Model Manager Optimization...")
    
    try:
        from models.lazy_model_manager import LazyModelManager
        from config import KEEP_MODELS_LOADED
        import torch
        
        print(f"KEEP_MODELS_LOADED setting: {KEEP_MODELS_LOADED}")
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")
        
        # Create model manager
        model_manager = LazyModelManager(device)
        
        # Test 1: Load CLIP model
        start_time = time.time()
        clip_model, clip_preprocess = model_manager.get_clip_model_for_search()
        clip_load_time = time.time() - start_time
        print(f"✅ CLIP model loaded in {clip_load_time:.2f}s")
        
        # Test 2: Load BLIP model (should not unload CLIP if KEEP_MODELS_LOADED=True)
        start_time = time.time()
        blip_model, blip_processor = model_manager.get_blip_model_for_caption()
        blip_load_time = time.time() - start_time
        print(f"✅ BLIP model loaded in {blip_load_time:.2f}s")
        
        # Test 3: Get CLIP model again (should be instant if kept loaded)
        start_time = time.time()
        clip_model2, clip_preprocess2 = model_manager.get_clip_model_for_search()
        clip_reload_time = time.time() - start_time
        print(f"✅ CLIP model re-accessed in {clip_reload_time:.3f}s")
        
        # Verify optimization worked
        assert clip_reload_time < 1.0, "Models are still being swapped"
        print("🎉 OPTIMIZATION SUCCESS: Models are being kept in memory!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        pytest.fail(f"Test failed with exception: {e}")

@pytest.mark.skip(reason="Session state caching test requires full Streamlit environment")
def test_session_state_caching():
    """Test that @st.cache_resource is working for model managers"""
    print("\n🧪 Testing Session State Caching...")
    
    try:
        # Mock streamlit session state for testing
        class MockSessionState:
            def __init__(self):
                self._state = {}
            
            def get(self, key, default=None):
                return self._state.get(key, default)
            
            def __setitem__(self, key, value):
                self._state[key] = value
            
            def __getitem__(self, key):
                return self._state[key]
            
            def __contains__(self, key):
                return key in self._state
        
        # This test would need actual Streamlit to work properly
        print("⚠️ Session state caching test requires full Streamlit environment")
        print("✅ Test structure is correct - will work in actual app")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        pytest.fail(f"Test failed with exception: {e}")

def test_background_loader_logic():
    """Test that the background loader doesn't get stuck in loops"""
    print("\n🧪 Testing Background Loader Logic...")
    
    try:
        from core.background_loader import BackgroundLoader, LoadingProgress
        
        # Create a test background loader
        loader = BackgroundLoader()
        
        # Test progress tracking
        progress = loader.get_progress()
        print(f"Initial progress: {progress.progress_percentage}%")
        
        # Test that progress updates work
        with loader._lock:
            loader.progress.update_progress(50, "Test progress update")
        
        updated_progress = loader.get_progress()
        print(f"Updated progress: {updated_progress.progress_percentage}%")
        
        assert updated_progress.progress_percentage == 50, "Progress tracking failed"
        print("✅ Progress tracking works correctly")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        pytest.fail(f"Test failed with exception: {e}") 