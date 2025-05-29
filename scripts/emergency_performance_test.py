# 🚨 Emergency Performance Test - Sprint 03 Recovery
# 📌 Purpose: Measure current performance and track recovery progress
# 🎯 Mission: Verify fixes and monitor restoration to Sprint 02 baseline

import sys
import os
import time
import logging
from datetime import datetime

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
        if startup_time < 1.0:
            print("🎉 EXCELLENT: Startup time is under 1 second!")
            return "EXCELLENT"
        elif startup_time < 5.0:
            print("✅ GOOD: Startup time is acceptable")
            return "GOOD"
        elif startup_time < 15.0:
            print("⚠️ SLOW: Startup time is concerning")
            return "SLOW"
        else:
            print("❌ CRITICAL: Startup time is unacceptable")
            return "CRITICAL"
            
    except Exception as e:
        print(f"❌ Startup test failed: {e}")
        return "FAILED"

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
        if clip_reaccess_time < 0.1 and blip_time < 10.0:
            print("🎉 EXCELLENT: Model loading is optimized!")
            return "EXCELLENT"
        elif clip_reaccess_time < 1.0 and blip_time < 30.0:
            print("✅ GOOD: Model loading is acceptable")
            return "GOOD"
        else:
            print("❌ CRITICAL: Model loading is too slow")
            return "CRITICAL"
            
    except Exception as e:
        print(f"❌ Model loading test failed: {e}")
        return "FAILED"

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
        if second_call_time < 0.01 and db_second_call_time < 0.01:
            print("🎉 EXCELLENT: Caching is working perfectly!")
            return "EXCELLENT"
        elif second_call_time < 0.1 and db_second_call_time < 0.1:
            print("✅ GOOD: Caching is working well")
            return "GOOD"
        else:
            print("❌ CRITICAL: Caching is not working properly")
            return "CRITICAL"
            
    except Exception as e:
        print(f"❌ Session state caching test failed: {e}")
        return "FAILED"

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
        prep_started = loader.start_background_preparation()
        print(f"Background preparation started: {prep_started}")
        
        # Wait a moment and check progress
        time.sleep(1)
        progress = loader.get_progress()
        print(f"Progress after 1s: {progress.progress_percentage}%")
        
        if not progress.error_occurred:
            print("✅ Background loader is functioning")
            return "GOOD"
        else:
            print(f"❌ Background loader has errors: {progress.error_message}")
            return "FAILED"
            
    except Exception as e:
        print(f"❌ Background loader test failed: {e}")
        return "FAILED"

def generate_performance_report():
    """Generate a comprehensive performance report"""
    print("=" * 60)
    print("🚨 EMERGENCY PERFORMANCE TEST REPORT")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Purpose: Sprint 03 Recovery Progress Tracking")
    print()
    
    # Run all tests
    startup_result = test_startup_performance()
    model_result = test_model_loading_performance()
    caching_result = test_session_state_caching()
    loader_result = test_background_loader()
    
    # Overall assessment
    print("\n" + "=" * 60)
    print("📊 OVERALL ASSESSMENT")
    print("=" * 60)
    
    results = [startup_result, model_result, caching_result, loader_result]
    
    if all(r in ["EXCELLENT", "GOOD"] for r in results):
        overall = "🎉 RECOVERY SUCCESSFUL"
        status = "Performance has been restored!"
    elif any(r == "CRITICAL" for r in results):
        overall = "🚨 CRITICAL ISSUES REMAIN"
        status = "Immediate action required!"
    elif any(r == "FAILED" for r in results):
        overall = "❌ SYSTEM FAILURES"
        status = "Major fixes needed!"
    else:
        overall = "⚠️ PARTIAL RECOVERY"
        status = "Some improvements made, more work needed."
    
    print(f"Overall Status: {overall}")
    print(f"Assessment: {status}")
    print()
    print("Component Results:")
    print(f"  - Startup Performance: {startup_result}")
    print(f"  - Model Loading: {model_result}")
    print(f"  - Session Caching: {caching_result}")
    print(f"  - Background Loader: {loader_result}")
    
    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    if startup_result in ["SLOW", "CRITICAL"]:
        print("  - 🚨 URGENT: Fix startup performance issues")
    if model_result == "CRITICAL":
        print("  - 🚨 URGENT: Fix model loading performance")
    if caching_result == "CRITICAL":
        print("  - 🚨 URGENT: Restore session state caching")
    if loader_result == "FAILED":
        print("  - 🚨 URGENT: Fix background loader functionality")
    
    if overall == "🎉 RECOVERY SUCCESSFUL":
        print("  - ✅ Continue with Sprint 03 advanced features")
        print("  - ✅ Implement performance monitoring")
        print("  - ✅ Document successful recovery patterns")
    
    print("\n" + "=" * 60)
    return overall

def main():
    """Run emergency performance test"""
    try:
        overall_result = generate_performance_report()
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"emergency_performance_results_{timestamp}.json"
        
        import json
        results = {
            "timestamp": timestamp,
            "overall_result": overall_result,
            "test_date": datetime.now().isoformat(),
            "purpose": "Sprint 03 Recovery Progress Tracking"
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Results saved to: {results_file}")
        
        return overall_result == "🎉 RECOVERY SUCCESSFUL"
        
    except Exception as e:
        print(f"❌ Emergency performance test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 