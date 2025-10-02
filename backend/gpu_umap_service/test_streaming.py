#!/usr/bin/env python3
"""
Test script for the streaming UMAP service.
This script tests both small and large dataset processing.
"""

import asyncio
import time
import numpy as np
import requests
import json
from typing import List, Dict, Any

# Configuration
BASE_URL = "http://localhost:8003"
UMAP_ENDPOINT = f"{BASE_URL}/umap/streaming/umap"
CLUSTER_ENDPOINT = f"{BASE_URL}/umap/streaming/cluster"
STATUS_ENDPOINT = f"{BASE_URL}/umap/streaming/status"
CANCEL_ENDPOINT = f"{BASE_URL}/umap/streaming/cancel"

def generate_test_data(n_points: int, n_features: int = 512) -> List[List[float]]:
    """Generate test data for UMAP processing."""
    print(f"Generating {n_points} points with {n_features} features...")
    return np.random.rand(n_points, n_features).tolist()

def test_small_dataset():
    """Test small dataset (should complete immediately)."""
    print("\n=== Testing Small Dataset (500 points) ===")
    
    data = generate_test_data(500)
    
    # Test UMAP
    print("Testing UMAP...")
    response = requests.post(UMAP_ENDPOINT, json={
        "data": data,
        "n_components": 2,
        "n_neighbors": 15,
        "min_dist": 0.1,
        "metric": "cosine",
        "random_state": 42
    })
    
    print(f"UMAP Response Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"UMAP Result: {result}")
        
        if result.get("job_id") == "immediate":
            print("✅ Small dataset processed immediately")
        else:
            print(f"⚠️ Unexpected job_id: {result.get('job_id')}")
    else:
        print(f"❌ UMAP failed: {response.text}")
    
    # Test Clustering
    print("\nTesting Clustering...")
    response = requests.post(CLUSTER_ENDPOINT, json={
        "data": data,
        "algorithm": "dbscan",
        "eps": 0.5,
        "min_samples": 5
    })
    
    print(f"Clustering Response Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Clustering Result: {result}")
        
        if result.get("job_id") == "immediate":
            print("✅ Small dataset clustering completed immediately")
        else:
            print(f"⚠️ Unexpected job_id: {result.get('job_id')}")
    else:
        print(f"❌ Clustering failed: {response.text}")

def test_large_dataset():
    """Test large dataset (should use streaming)."""
    print("\n=== Testing Large Dataset (5000 points) ===")
    
    data = generate_test_data(5000)
    
    # Test UMAP
    print("Testing UMAP...")
    response = requests.post(UMAP_ENDPOINT, json={
        "data": data,
        "n_components": 2,
        "n_neighbors": 15,
        "min_dist": 0.1,
        "metric": "cosine",
        "random_state": 42
    })
    
    print(f"UMAP Response Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"UMAP Result: {result}")
        
        if result.get("job_id") != "immediate":
            job_id = result.get("job_id")
            print(f"✅ Large dataset streaming started with job_id: {job_id}")
            
            # Poll for completion
            print("Polling for completion...")
            max_polls = 60  # 60 seconds max
            poll_count = 0
            
            while poll_count < max_polls:
                time.sleep(1)
                poll_count += 1
                
                status_response = requests.get(f"{STATUS_ENDPOINT}/{job_id}")
                if status_response.status_code == 200:
                    status = status_response.json()
                    print(f"Status: {status.get('status')} - {status.get('progress_percentage', 0):.1f}%")
                    
                    if status.get("status") == "completed":
                        print("✅ Large dataset UMAP completed successfully")
                        print(f"Processing time: {status.get('processing_time', 0):.2f}s")
                        break
                    elif status.get("status") == "failed":
                        print(f"❌ UMAP failed: {status.get('error')}")
                        break
                else:
                    print(f"❌ Status check failed: {status_response.text}")
                    break
            else:
                print("❌ UMAP timed out")
        else:
            print("⚠️ Large dataset was processed immediately (unexpected)")
    else:
        print(f"❌ UMAP failed: {response.text}")

def test_service_health():
    """Test if the service is running."""
    print("=== Testing Service Health ===")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Service is healthy")
            return True
        else:
            print(f"❌ Service health check failed: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Service not reachable: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Streaming UMAP Service Tests")
    print(f"Testing service at: {BASE_URL}")
    
    # Check service health first
    if not test_service_health():
        print("\n❌ Service is not available. Please start the service first:")
        print("cd backend/gpu_umap_service")
        print("uvicorn main:app --host 0.0.0.0 --port 8003 --reload")
        return
    
    # Run tests
    test_small_dataset()
    test_large_dataset()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main() 