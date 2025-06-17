#!/usr/bin/env python3
"""
Simple test script to check if the pipeline components are working
"""
import requests
import json
import os
from pathlib import Path

def test_ml_service():
    """Test the ML inference service"""
    print("Testing ML Inference Service (port 8001)...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8001/health", timeout=5)
        print(f"Health check: {response.status_code}")
        
        # Test text embedding
        text_data = {"text": "test image"}
        response = requests.post(
            "http://localhost:8001/api/v1/embeddings/text",
            json=text_data,
            timeout=10
        )
        print(f"Text embedding: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Embedding dimension: {len(result.get('embedding', []))}")
        
        return True
    except Exception as e:
        print(f"ML Service error: {e}")
        return False

def test_ingestion_service():
    """Test the ingestion orchestration service"""
    print("\nTesting Ingestion Orchestration Service (port 8000)...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check: {response.status_code}")
        
        # Test collections endpoint
        response = requests.get("http://localhost:8000/api/v1/collections", timeout=5)
        print(f"Collections list: {response.status_code}")
        if response.status_code == 200:
            collections = response.json()
            print(f"Available collections: {collections}")
        
        return True
    except Exception as e:
        print(f"Ingestion Service error: {e}")
        return False

def test_qdrant():
    """Test Qdrant directly"""
    print("\nTesting Qdrant directly...")
    
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        print(f"Qdrant collections: {response.status_code}")
        if response.status_code == 200:
            collections = response.json()
            print(f"Qdrant collections: {collections}")
        return True
    except Exception as e:
        print(f"Qdrant error: {e}")
        return False

def test_image_directories():
    """Test if the image directories exist and have content"""
    print("\nTesting image directories...")
    
    # Test Library Test directory
    library_test = Path("Library Test")
    if library_test.exists():
        images = list(library_test.glob("*.jpg")) + list(library_test.glob("*.png"))
        print(f"Library Test: {len(images)} images found")
    else:
        print("Library Test directory not found")
    
    # Test dng test directory
    dng_test = Path(r"C:\Users\aitor\OneDrive\Escritorio\dng test")
    if dng_test.exists():
        images = list(dng_test.glob("*.dng")) + list(dng_test.glob("*.jpg"))
        print(f"DNG Test: {len(images)} images found")
    else:
        print("DNG Test directory not found")

if __name__ == "__main__":
    print("=== Pipeline Component Test ===")
    
    # Test image directories first
    test_image_directories()
    
    # Test services
    ml_ok = test_ml_service()
    ingestion_ok = test_ingestion_service()
    qdrant_ok = test_qdrant()
    
    print("\n=== Summary ===")
    print(f"ML Service: {'✓' if ml_ok else '✗'}")
    print(f"Ingestion Service: {'✓' if ingestion_ok else '✗'}")
    print(f"Qdrant: {'✓' if qdrant_ok else '✗'}")
    
    if ml_ok and qdrant_ok:
        print("\n✓ Core pipeline components are working!")
        print("You can proceed with image ingestion using the ML service directly.")
    else:
        print("\n✗ Some components are not working. Check the services.") 