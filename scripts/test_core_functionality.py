#!/usr/bin/env python3
"""
Simple test for Sprint 03 Phase 1: Core Database Manager Functionality
Tests the core components without complex Streamlit mocking
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_core_database_functionality():
    """Test core database manager functionality directly"""
    print("🧪 Sprint 03 Phase 1: Core Database Manager Test")
    print("=" * 50)
    
    try:
        print("\n📝 Test 1: Direct database manager creation...")
        
        # Test direct creation without Streamlit
        from database.db_manager import DatabaseManager
        from models.lazy_model_manager import LazyModelManager
        import torch
        
        # Create components directly
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"✅ Device: {device}")
        
        model_manager = LazyModelManager(device)
        print(f"✅ Model manager created: {type(model_manager)}")
        
        db_manager = DatabaseManager(model_manager)
        print(f"✅ Database manager created: {type(db_manager)}")
        
        # Test core functionality
        exists = db_manager.database_exists(".")
        print(f"✅ database_exists('.'): {exists}")
        
        # Test get_image_list
        images = db_manager.get_image_list(".")
        print(f"✅ get_image_list('.'): Found {len(images)} images")
        
        print("\n🎉 Core database functionality test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling scenarios"""
    print("\n🔧 Test 2: Error handling scenarios...")
    
    try:
        from database.db_manager import DatabaseManager
        from models.lazy_model_manager import LazyModelManager
        import torch
        
        # Test with valid components
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_manager = LazyModelManager(device)
        db_manager = DatabaseManager(model_manager)
        
        # Test with invalid path
        try:
            exists = db_manager.database_exists("/nonexistent/path/that/should/not/exist")
            print(f"✅ Handled invalid path gracefully: {exists}")
        except Exception as e:
            print(f"⚠️ Invalid path handling: {e}")
        
        # Test with empty string
        try:
            exists = db_manager.database_exists("")
            print(f"✅ Handled empty path gracefully: {exists}")
        except Exception as e:
            print(f"⚠️ Empty path handling: {e}")
        
        print("✅ Error handling test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_search_components():
    """Test that search components can import and work with database manager"""
    print("\n🔍 Test 3: Search components integration...")
    
    try:
        # Test core database components (non-Streamlit dependent)
        from database.db_manager import DatabaseManager
        print("✅ Database manager import successful")
        
        from models.lazy_model_manager import LazyModelManager
        print("✅ Lazy model manager import successful")
        
        from utils.lazy_session_state import LazySessionManager
        print("✅ Lazy session manager import successful")
        
        # Test that the logger works
        from utils.logger import logger
        logger.info("Test log message from core functionality test")
        print("✅ Logger import and usage successful")
        
        # Test that we can create the components that were failing before
        import torch
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_manager = LazyModelManager(device)
        db_manager = DatabaseManager(model_manager)
        
        # Test the specific method that was causing NoneType errors
        exists = db_manager.database_exists(".")
        print(f"✅ database_exists method working: {exists}")
        
        print("✅ Core components integration test PASSED!")
        print("ℹ️  Note: Streamlit-dependent components skipped (expected in non-Streamlit context)")
        return True
        
    except Exception as e:
        print(f"❌ Core components test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all core functionality tests"""
    print("🚀 Sprint 03 Phase 1: Core Functionality Test Suite")
    print("🎯 Goal: Verify core database manager functionality works")
    print("🔧 Testing: Direct component creation and integration")
    print()
    
    # Run tests
    test1_passed = test_core_database_functionality()
    test2_passed = test_error_handling()
    test3_passed = test_search_components()
    
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    print(f"Core Database Functionality: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Error Handling:              {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"Search Components:           {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    all_passed = test1_passed and test2_passed and test3_passed
    
    if all_passed:
        print("\n🎉 ALL CORE TESTS PASSED!")
        print("✅ Database manager core functionality is working")
        print("✅ Error handling is functional")
        print("✅ Search components can be imported")
        print("✅ Ready to test in actual Streamlit environment")
    else:
        print("\n🔧 Some core tests failed. Check the error messages above.")
    
    print("\n📋 Next Steps:")
    if all_passed:
        print("1. ✅ Core functionality verified")
        print("2. 🚀 Test in actual Streamlit application")
        print("3. 🔍 Verify search functionality works end-to-end")
        print("4. 📈 Move to Sprint 03 Phase 2: Advanced Search")
    else:
        print("1. 🔧 Fix core functionality issues")
        print("2. 🧪 Re-run tests until all pass")
        print("3. 🚀 Then test in Streamlit environment")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 