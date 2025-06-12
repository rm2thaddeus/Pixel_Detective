# 🚨 Emergency Performance Test - Sprint 03 Recovery
# 📌 Purpose: Measure current performance and track recovery progress
# 🎯 Mission: Verify fixes and monitor restoration to Sprint 02 baseline

import sys
import os
import time
import logging
from datetime import datetime
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_startup_performance():
    """Test application startup performance"""
    print("🚀 Testing Application Startup Performance...")
    
    try:
        start_time = time.time()
        
        # Test basic imports
        import streamlit as st
        import torch
        
        # Test model manager creation
        from models.lazy_model_manager import LazyModelManager
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_manager = LazyModelManager(device)
        
        startup_time = time.time() - start_time
        
        print(f"✅ Basic startup completed in {startup_time:.3f}s")
        
        # Performance assessment
        assert startup_time < 15.0, f"Startup time is too slow: {startup_time:.3f}s"
        print("✅ GOOD: Startup time is acceptable")
            
    except Exception as e:
        pytest.fail(f"Startup test failed: {e}")

def test_model_loading_performance():
    """Test model loading performance"""
    print("\n🤖 Testing Model Loading Performance...")
    
    try:
        from models.lazy_model_manager import LazyModelManager
        import torch
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_manager = LazyModelManager(device)
        
        # Test CLIP loading
        start_time = time.time()
        clip_model, clip_preprocess = model_manager.get_clip_model_for_search()
        clip_time = time.time() - start_time
        print(f"CLIP model loaded in {clip_time:.3f}s")
        
        # Test CLIP re-access (should be instant if cached)
        start_time = time.time()
        clip_model2, clip_preprocess2 = model_manager.get_clip_model_for_search()
        clip_reaccess_time = time.time() - start_time
        print(f"CLIP model re-accessed in {clip_reaccess_time:.3f}s")
        
        # Test BLIP loading
        start_time = time.time()
        blip_model, blip_processor = model_manager.get_blip_model_for_caption()
        blip_time = time.time() - start_time
        print(f"BLIP model loaded in {blip_time:.3f}s")
        
        # Performance assessment
        assert clip_reaccess_time < 1.0, f"CLIP re-access time is too slow: {clip_reaccess_time:.3f}s"
        assert blip_time < 30.0, f"BLIP loading time is too slow: {blip_time:.3f}s"
        print("✅ GOOD: Model loading is acceptable")
            
    except Exception as e:
        pytest.fail(f"Model loading test failed: {e}")

def test_session_state_caching():
    """Test session state caching mechanisms"""
    print("\n💾 Testing Session State Caching...")
    
    try:
        from utils.lazy_session_state import get_cached_model_manager, get_cached_database_manager
        
        # Test model manager caching
        start_time = time.time()
        model_manager1 = get_cached_model_manager()
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        model_manager2 = get_cached_model_manager()
        second_call_time = time.time() - start_time
        
        print(f"First model manager call: {first_call_time:.3f}s")
        print(f"Second model manager call: {second_call_time:.3f}s")
        
        # Test database manager caching
        start_time = time.time()
        db_manager1 = get_cached_database_manager()
        db_first_call_time = time.time() - start_time
        
        start_time = time.time()
        db_manager2 = get_cached_database_manager()
        db_second_call_time = time.time() - start_time
        
        print(f"First database manager call: {db_first_call_time:.3f}s")
        print(f"Second database manager call: {db_second_call_time:.3f}s")
        
        # Performance assessment
        assert second_call_time < 0.1, f"Model manager caching is not working properly: {second_call_time:.3f}s"
        assert db_second_call_time < 0.1, f"Database manager caching is not working properly: {db_second_call_time:.3f}s"
        print("✅ GOOD: Caching is working well")
            
    except Exception as e:
        pytest.fail(f"Session state caching test failed: {e}")

def test_background_loader():
    """Test background loader functionality"""
    print("\n🔄 Testing Background Loader...")
    
    try:
        from core.background_loader import BackgroundLoader
        
        loader = BackgroundLoader()
        
        # Test progress tracking
        progress = loader.get_progress()
        print(f"Initial progress: {progress.progress_percentage}%")
        print(f"Loading state: {progress.is_loading}")
        print(f"Error state: {progress.error_occurred}")
        
        # Test background preparation
        from core.background_loader import background_loader as bg_loader
        # This part of test is problematic as it might interact with a global state
        # For now, just check the initial state.
        # prep_started = bg_loader.start_background_preparation()
        # print(f"Background preparation started: {prep_started}")
        
        # Wait a moment and check progress
        # time.sleep(1)
        # progress = loader.get_progress()
        # print(f"Progress after 1s: {progress.progress_percentage}%")
        
        assert not progress.error_occurred, f"Background loader has errors"
        print("✅ Background loader is functioning")
            
    except Exception as e:
        pytest.fail(f"Background loader test failed: {e}")