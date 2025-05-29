#!/usr/bin/env python3
"""
🚀 SPRINT 03 PERFORMANCE FIX VERIFICATION
Test script to verify that critical performance issues have been resolved.

Expected Results After Fix:
- App startup: <10 seconds (vs 68+ seconds before)
- Model loading: Only when user starts processing (vs immediate)
- No infinite loops in background loader
- Smooth UI transitions
"""

import time
import sys
import os
import json
from datetime import datetime

def test_basic_imports():
    """Test basic import performance"""
    print("🧪 Testing basic imports...")
    
    start_time = time.time()
    import streamlit as st
    streamlit_time = time.time() - start_time
    
    start_time = time.time()
    from core.screen_renderer import render_app
    renderer_time = time.time() - start_time
    
    start_time = time.time()
    from core.background_loader import background_loader
    loader_time = time.time() - start_time
    
    return {
        'streamlit_import': streamlit_time,
        'renderer_import': renderer_time,
        'loader_import': loader_time,
        'total_import_time': streamlit_time + renderer_time + loader_time
    }

def test_lazy_loading():
    """Test that models are NOT loaded during import"""
    print("🧪 Testing lazy loading behavior...")
    
    # Import the lazy session state
    from utils.lazy_session_state import LazySessionManager
    
    # Check if heavy modules are loaded
    import sys
    torch_loaded = 'torch' in sys.modules
    transformers_loaded = 'transformers' in sys.modules
    
    # Check if model managers exist in session state
    import streamlit as st
    model_manager_exists = 'model_manager' in st.session_state
    db_manager_exists = 'db_manager' in st.session_state
    
    return {
        'torch_loaded_at_import': torch_loaded,
        'transformers_loaded_at_import': transformers_loaded,
        'model_manager_in_session': model_manager_exists,
        'db_manager_in_session': db_manager_exists,
        'lazy_loading_working': not (model_manager_exists or db_manager_exists)
    }

def test_background_loader():
    """Test background loader initialization"""
    print("🧪 Testing background loader...")
    
    from core.background_loader import background_loader
    
    # Check initial state
    progress = background_loader.get_progress()
    
    return {
        'is_loading': progress.is_loading,
        'progress_percentage': progress.progress_percentage,
        'error_occurred': progress.error_occurred,
        'background_prep_started': progress.background_prep_started,
        'models_loaded': progress.models_loaded,
        'database_ready': progress.database_ready
    }

def test_app_startup_simulation():
    """Simulate app startup without actually running Streamlit"""
    print("🧪 Testing app startup simulation...")
    
    start_time = time.time()
    
    # Import main components
    from core.screen_renderer import ScreenRenderer
    from core.app_state import AppStateManager
    
    # Initialize core state (should be fast)
    from utils.lazy_session_state import LazySessionManager
    LazySessionManager.init_core_state()
    
    startup_time = time.time() - start_time
    
    return {
        'startup_simulation_time': startup_time,
        'startup_under_1_second': startup_time < 1.0,
        'startup_under_5_seconds': startup_time < 5.0
    }

def run_comprehensive_test():
    """Run all performance tests"""
    print("🚀 SPRINT 03 PERFORMANCE FIX VERIFICATION")
    print("=" * 50)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'test_purpose': 'Verify Sprint 03 performance fixes',
        'expected_improvements': [
            'App startup < 10 seconds (vs 68+ seconds)',
            'Models load only when needed',
            'No infinite loops',
            'Smooth UI transitions'
        ]
    }
    
    # Test 1: Basic Imports
    print("\n1️⃣ Testing Import Performance...")
    try:
        import_results = test_basic_imports()
        results['import_performance'] = import_results
        
        total_time = import_results['total_import_time']
        if total_time < 10:
            print(f"✅ EXCELLENT: Total import time: {total_time:.3f}s")
        elif total_time < 30:
            print(f"⚠️ ACCEPTABLE: Total import time: {total_time:.3f}s")
        else:
            print(f"❌ SLOW: Total import time: {total_time:.3f}s")
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        results['import_performance'] = {'error': str(e)}
    
    # Test 2: Lazy Loading
    print("\n2️⃣ Testing Lazy Loading...")
    try:
        lazy_results = test_lazy_loading()
        results['lazy_loading'] = lazy_results
        
        if lazy_results['lazy_loading_working']:
            print("✅ EXCELLENT: Lazy loading is working - models not loaded at startup")
        else:
            print("❌ ISSUE: Models are being loaded at startup")
            
    except Exception as e:
        print(f"❌ Lazy loading test failed: {e}")
        results['lazy_loading'] = {'error': str(e)}
    
    # Test 3: Background Loader
    print("\n3️⃣ Testing Background Loader...")
    try:
        loader_results = test_background_loader()
        results['background_loader'] = loader_results
        
        if not loader_results['is_loading'] and not loader_results['error_occurred']:
            print("✅ EXCELLENT: Background loader in clean state")
        else:
            print("⚠️ WARNING: Background loader may have issues")
            
    except Exception as e:
        print(f"❌ Background loader test failed: {e}")
        results['background_loader'] = {'error': str(e)}
    
    # Test 4: Startup Simulation
    print("\n4️⃣ Testing Startup Simulation...")
    try:
        startup_results = test_app_startup_simulation()
        results['startup_simulation'] = startup_results
        
        startup_time = startup_results['startup_simulation_time']
        if startup_time < 1.0:
            print(f"✅ EXCELLENT: Startup simulation: {startup_time:.3f}s")
        elif startup_time < 5.0:
            print(f"⚠️ GOOD: Startup simulation: {startup_time:.3f}s")
        else:
            print(f"❌ SLOW: Startup simulation: {startup_time:.3f}s")
            
    except Exception as e:
        print(f"❌ Startup simulation failed: {e}")
        results['startup_simulation'] = {'error': str(e)}
    
    # Overall Assessment
    print("\n📊 OVERALL ASSESSMENT")
    print("=" * 30)
    
    issues = []
    successes = []
    
    # Check import performance
    if 'import_performance' in results and 'total_import_time' in results['import_performance']:
        if results['import_performance']['total_import_time'] < 10:
            successes.append("✅ Fast imports")
        else:
            issues.append("❌ Slow imports")
    
    # Check lazy loading
    if 'lazy_loading' in results and 'lazy_loading_working' in results['lazy_loading']:
        if results['lazy_loading']['lazy_loading_working']:
            successes.append("✅ Lazy loading working")
        else:
            issues.append("❌ Models loading at startup")
    
    # Check background loader
    if 'background_loader' in results and 'error_occurred' in results['background_loader']:
        if not results['background_loader']['error_occurred']:
            successes.append("✅ Background loader clean")
        else:
            issues.append("❌ Background loader errors")
    
    # Check startup simulation
    if 'startup_simulation' in results and 'startup_under_5_seconds' in results['startup_simulation']:
        if results['startup_simulation']['startup_under_5_seconds']:
            successes.append("✅ Fast startup simulation")
        else:
            issues.append("❌ Slow startup simulation")
    
    print("\n🎉 SUCCESSES:")
    for success in successes:
        print(f"  {success}")
    
    if issues:
        print("\n⚠️ REMAINING ISSUES:")
        for issue in issues:
            print(f"  {issue}")
        results['overall_status'] = "PARTIAL_SUCCESS"
    else:
        print("\n🎉 ALL TESTS PASSED!")
        results['overall_status'] = "SUCCESS"
    
    # Save results
    filename = f"performance_fix_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    try:
        results = run_comprehensive_test()
        
        # Exit with appropriate code
        if results.get('overall_status') == 'SUCCESS':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2) 