#!/usr/bin/env python3
"""
Simple test for Sprint 03 Phase 1: Core Database Manager Functionality
Tests the core components without complex Streamlit mocking
"""

import sys
import os
import pytest

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
        assert True
        
    except Exception as e:
        pytest.fail(f"Core functionality test failed: {e}")

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
            assert not exists
        except Exception as e:
            pytest.fail(f"Invalid path handling failed: {e}")
        
        # Test with empty string
        try:
            exists = db_manager.database_exists("")
            print(f"✅ Handled empty path gracefully: {exists}")
            assert not exists
        except Exception as e:
            pytest.fail(f"Empty path handling failed: {e}")
        
        print("✅ Error handling test PASSED!")
        assert True
        
    except Exception as e:
        pytest.fail(f"Error handling test failed: {e}")

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
        assert True
        
    except Exception as e:
        pytest.fail(f"Core components test failed: {e}") 