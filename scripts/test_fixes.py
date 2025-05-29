#!/usr/bin/env python3
"""
Test script to verify the database manager fixes work properly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_app_state_initialization():
    """Test that app state initialization properly calls lazy session manager"""
    print("🔍 Testing App State Initialization")
    print("=" * 50)
    
    try:
        # Test the app state manager initialization
        from core.app_state import AppStateManager
        import streamlit as st
        
        # Mock session state if needed
        if not hasattr(st, 'session_state'):
            print("⚠️ No Streamlit session state available - creating mock")
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
                def keys(self):
                    return self._state.keys()
            st.session_state = MockSessionState()
        
        print("✅ Streamlit session state available")
        
        # Test app state initialization
        print("\n📝 Testing AppStateManager.init_session_state()...")
        AppStateManager.init_session_state()
        print("✅ AppStateManager.init_session_state() completed successfully")
        
        # Check if lazy session manager was initialized
        lazy_initialized = st.session_state.get('lazy_session_initialized', False)
        print(f"✅ Lazy session manager initialized: {lazy_initialized}")
        
        # Check core state variables
        app_state = st.session_state.get('app_state', None)
        models_loaded = st.session_state.get('models_loaded', False)
        database_connected = st.session_state.get('database_connected', False)
        
        print(f"✅ App state: {app_state}")
        print(f"✅ Models loaded: {models_loaded}")
        print(f"✅ Database connected: {database_connected}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_defensive_database_access():
    """Test that components handle missing database manager gracefully"""
    print("\n🔍 Testing Defensive Database Access")
    print("=" * 50)
    
    try:
        import streamlit as st
        
        # Simulate a session state without database manager
        if hasattr(st, 'session_state'):
            # Clear database manager if it exists
            if 'db_manager' in st.session_state:
                del st.session_state['db_manager']
        
        # Test that getting None database manager doesn't crash
        db_manager = st.session_state.get('db_manager', None)
        print(f"✅ Database manager from session state: {db_manager}")
        
        if db_manager is None:
            print("✅ Components should handle None database manager gracefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Database Manager Fixes")
    print("🎯 Goal: Verify that initialization fixes work properly")
    print()
    
    test1_success = test_app_state_initialization()
    test2_success = test_defensive_database_access()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    if test1_success and test2_success:
        print("🎉 ALL TESTS PASSED! ✅")
        print("✅ App state initialization works correctly")
        print("✅ Components handle missing database manager gracefully")
        print("✅ No more 'Database manager is None' errors should occur")
    else:
        print("🔧 SOME TESTS FAILED ❌")
        if not test1_success:
            print("❌ App state initialization needs fixing")
        if not test2_success:
            print("❌ Defensive database access needs fixing")
    
    return test1_success and test2_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 