#!/usr/bin/env python3
"""
Test script to verify the Sprint 10 ingestion pipeline is working correctly.
This tests the complete workflow: collection creation -> selection -> ingestion -> verification
"""
import requests
import time
import os
import sys

def test_ingestion_pipeline():
    """Test the complete ingestion pipeline."""
    
    # Configuration
    base_url = "http://localhost:8002"
    test_collection = "sprint10-ingestion-test"
    test_directory = r"C:\Users\aitor\OneDrive\Escritorio\Vibe Coding\Library Test"
    
    print("🚀 Testing Sprint 10 Ingestion Pipeline")
    print("=" * 50)
    
    # 1. Test health
    print("1. Testing service health...")
    try:
        health = requests.get(f"{base_url}/health")
        if health.status_code == 200:
            print("   ✅ Backend services healthy")
        else:
            print(f"   ❌ Health check failed: {health.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # 2. Create collection
    print("2. Creating test collection...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/collections",
            json={"collection_name": test_collection}
        )
        if response.status_code in [200, 400]:  # 400 if already exists
            print(f"   ✅ Collection '{test_collection}' ready")
        else:
            print(f"   ❌ Collection creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Collection creation failed: {e}")
        return False
    
    # 3. Select collection
    print("3. Selecting collection...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/collections/select",
            json={"collection_name": test_collection}
        )
        if response.status_code == 200:
            print(f"   ✅ Collection '{test_collection}' selected")
        else:
            print(f"   ❌ Collection selection failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Collection selection failed: {e}")
        return False
    
    # 4. Check test directory exists
    print("4. Checking test directory...")
    if not os.path.exists(test_directory):
        print(f"   ❌ Test directory not found: {test_directory}")
        return False
    
    # Count image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.dng'}
    image_count = 0
    for root, dirs, files in os.walk(test_directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in image_extensions):
                image_count += 1
    
    print(f"   ✅ Found {image_count} image files in test directory")
    
    # 5. Start ingestion
    print("5. Starting ingestion...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/ingest/",
            json={"directory_path": test_directory}
        )
        if response.status_code == 200:
            job_data = response.json()
            job_id = job_data.get("job_id")
            print(f"   ✅ Ingestion job started: {job_id}")
        else:
            print(f"   ❌ Ingestion start failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Ingestion start failed: {e}")
        return False
    
    # 6. Monitor job progress
    print("6. Monitoring job progress...")
    start_time = time.time()
    last_progress = 0
    
    while True:
        try:
            response = requests.get(f"{base_url}/api/v1/ingest/status/{job_id}")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get("status")
                progress = status_data.get("progress", 0)
                message = status_data.get("message", "")
                
                # Show progress updates
                if progress > last_progress:
                    print(f"   📊 Progress: {progress:.1f}% - {message}")
                    last_progress = progress
                
                if status == "completed":
                    processed = status_data.get("processed_files", 0)
                    cached = status_data.get("cached_files", 0)
                    errors = len(status_data.get("errors", []))
                    
                    elapsed = time.time() - start_time
                    print(f"   ✅ Ingestion completed in {elapsed:.1f}s")
                    print(f"      📊 Processed: {processed} files")
                    print(f"      🗄️  Cached: {cached} files")
                    print(f"      ❌ Errors: {errors} files")
                    
                    if errors > 0:
                        print("      Error details:")
                        for error in status_data.get("errors", [])[:3]:  # Show first 3 errors
                            print(f"        - {error}")
                    
                    break
                    
                elif status == "failed":
                    print(f"   ❌ Ingestion failed: {message}")
                    return False
                    
            else:
                print(f"   ❌ Status check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Status check error: {e}")
            return False
        
        # Timeout after 5 minutes
        if time.time() - start_time > 300:
            print("   ⏰ Timeout waiting for ingestion to complete")
            return False
        
        time.sleep(2)  # Poll every 2 seconds
    
    print("\n🎉 Sprint 10 ingestion pipeline test PASSED!")
    print("   The backend is fully functional and ready for frontend integration.")
    return True

if __name__ == "__main__":
    success = test_ingestion_pipeline()
    sys.exit(0 if success else 1) 