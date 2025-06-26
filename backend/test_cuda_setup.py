#!/usr/bin/env python3
"""
Test script to verify CUDA setup and our implementation.
"""
import sys
import os
sys.path.append('ingestion_orchestration_fastapi_app')

import numpy as np
import time

print("=== CUDA Setup Test ===")

# Test 1: Check cupy availability
print("\n1. Testing CuPy availability:")
try:
    import cupy as cp
    print(f"✅ CuPy installed: {cp.__version__}")
    print(f"✅ CUDA available: {cp.cuda.is_available()}")
    if cp.cuda.is_available():
        print(f"✅ Device count: {cp.cuda.runtime.getDeviceCount()}")
        try:
            device_prop = cp.cuda.runtime.getDeviceProperties(0)
            print(f"✅ Device name: {device_prop['name'].decode()}")
        except:
            print("✅ Device detected (name unavailable)")
except ImportError as e:
    print(f"❌ CuPy not available: {e}")

# Test 2: Check cuML availability
print("\n2. Testing cuML availability:")
try:
    import cuml
    print(f"✅ cuML installed: {cuml.__version__}")
except ImportError as e:
    print(f"❌ cuML not available: {e}")

# Test 3: Test our cuml.accel approach
print("\n3. Testing cuml.accel acceleration:")
CUDA_ACCELERATION_ENABLED = False
try:
    import cuml.accel
    cuml.accel.install()
    CUDA_ACCELERATION_ENABLED = True
    print("✅ cuML.accel enabled successfully")
except ImportError:
    print("❌ cuML.accel not available, using CPU-only implementations")
except Exception as e:
    print(f"❌ Failed to enable CUDA acceleration: {e}")

# Test 4: Test basic UMAP functionality
print("\n4. Testing UMAP functionality:")
try:
    import umap
    print("✅ UMAP imported successfully")
    
    # Small test
    print("   Running small UMAP test...")
    X = np.random.rand(50, 512).astype(np.float32)
    start_time = time.time()
    reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42)
    result = reducer.fit_transform(X)
    duration = time.time() - start_time
    print(f"   ✅ UMAP test completed: {X.shape} -> {result.shape} in {duration:.2f}s")
    print(f"   CUDA acceleration: {'✅ Enabled' if CUDA_ACCELERATION_ENABLED else '❌ Disabled'}")
    
except Exception as e:
    print(f"❌ UMAP test failed: {e}")

# Test 5: Test clustering
print("\n5. Testing clustering algorithms:")
try:
    from sklearn.cluster import DBSCAN, KMeans
    print("✅ Clustering algorithms imported")
    
    # Test with small 2D data
    X_2d = np.random.rand(100, 2).astype(np.float32)
    
    # DBSCAN test
    start_time = time.time()
    dbscan = DBSCAN(eps=0.3, min_samples=5)
    labels = dbscan.fit_predict(X_2d)
    dbscan_time = time.time() - start_time
    print(f"   ✅ DBSCAN: {len(set(labels))} clusters in {dbscan_time:.3f}s")
    
    # K-Means test
    start_time = time.time()
    kmeans = KMeans(n_clusters=5, random_state=42)
    labels = kmeans.fit_predict(X_2d)
    kmeans_time = time.time() - start_time
    print(f"   ✅ K-Means: {len(set(labels))} clusters in {kmeans_time:.3f}s")
    
except Exception as e:
    print(f"❌ Clustering test failed: {e}")

# Test 6: Check our adaptive classes
print("\n6. Testing our adaptive ML classes:")
try:
    from ingestion_orchestration_fastapi_app.ml_algorithms import AdaptiveUMAP, AdaptiveDBSCAN, AdaptiveKMeans
    print("✅ Adaptive classes imported successfully")
    
    # Test AdaptiveUMAP
    print("   Testing AdaptiveUMAP...")
    adaptive_umap = AdaptiveUMAP(n_components=2, random_state=42)
    X_test = np.random.rand(25, 512).astype(np.float32)
    start_time = time.time()
    result, metrics = adaptive_umap.fit_transform(X_test)
    duration = time.time() - start_time
    print(f"   ✅ AdaptiveUMAP: {X_test.shape} -> {result.shape} in {duration:.2f}s")
    print(f"   CUDA enabled: {'✅ Yes' if adaptive_umap.cuda_enabled else '❌ No'}")
    print(f"   CuPy accelerated: {'✅ Yes' if adaptive_umap.cupy_accelerated else '❌ No'}")
    
except Exception as e:
    print(f"❌ Adaptive classes test failed: {e}")

print("\n=== Test Summary ===")
print(f"CUDA Support: {'✅ Available' if 'cp' in locals() and cp.cuda.is_available() else '❌ Not Available'}")
print(f"cuML Support: {'✅ Available' if 'cuml' in locals() else '❌ Not Available'}")
print(f"Acceleration: {'✅ Enabled' if CUDA_ACCELERATION_ENABLED else '❌ CPU Fallback'}")
print("\n✅ CUDA implementation test completed!") 