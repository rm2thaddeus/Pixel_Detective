#!/usr/bin/env python3
"""
Test script to demonstrate CuPy acceleration capabilities.
"""
import sys
import os
sys.path.append('ingestion_orchestration_fastapi_app')

import numpy as np
import time
import matplotlib.pyplot as plt
from typing import List, Tuple

print("=== CuPy Acceleration Demonstration ===")

# Test CuPy setup
try:
    import cupy as cp
    print(f"✅ CuPy version: {cp.__version__}")
    print(f"✅ CUDA available: {cp.cuda.is_available()}")
    if cp.cuda.is_available():
        device_count = cp.cuda.runtime.getDeviceCount()
        print(f"✅ GPU devices: {device_count}")
        for i in range(device_count):
            try:
                props = cp.cuda.runtime.getDeviceProperties(i)
                print(f"   Device {i}: {props['name'].decode()}")
            except:
                print(f"   Device {i}: Available")
except ImportError:
    print("❌ CuPy not available")
    sys.exit(1)

# Import our enhanced adaptive classes
try:
    from ingestion_orchestration_fastapi_app.ml_algorithms import (
        AdaptiveUMAP, AdaptiveDBSCAN, AdaptiveKMeans, 
        CuPyAccelerator, get_acceleration_status
    )
    print("\n✅ Enhanced adaptive ML classes imported")
    
    # Print acceleration status
    status = get_acceleration_status()
    print(f"Acceleration level: {status['acceleration_level']}")
    print(f"CuPy available: {status['cupy_available']}")
    print(f"GPU available: {status['gpu_available']}")
    
except ImportError as e:
    print(f"❌ Failed to import adaptive classes: {e}")
    sys.exit(1)

def benchmark_preprocessing(sizes: List[int]) -> List[Tuple[int, float, float, float]]:
    """Benchmark CuPy acceleration for preprocessing operations"""
    print("\n=== Preprocessing Benchmark ===")
    results = []
    
    for size in sizes:
        print(f"\nTesting dataset size: {size} x 512")
        X = np.random.randn(size, 512).astype(np.float32)
        
        # Test standardization
        start_time = time.time()
        _, cupy_used = CuPyAccelerator.standardize(X)
        cpu_time = time.time() - start_time
        
        # Test with forced CPU (for comparison)
        start_time = time.time()
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        _ = scaler.fit_transform(X)
        sklearn_time = time.time() - start_time
        
        speedup = sklearn_time / cpu_time if cpu_time > 0 else 1.0
        
        print(f"   Standardization: {cpu_time:.3f}s {'(CuPy)' if cupy_used else '(CPU)'}")
        print(f"   Sklearn baseline: {sklearn_time:.3f}s")
        print(f"   Speedup: {speedup:.2f}x")
        
        results.append((size, cpu_time, sklearn_time, speedup))
        
        # Test distance matrix for smaller datasets
        if size <= 1000:
            start_time = time.time()
            _, cupy_used = CuPyAccelerator.distance_matrix(X[:100])
            dist_time = time.time() - start_time
            print(f"   Distance matrix (100 samples): {dist_time:.3f}s {'(CuPy)' if cupy_used else '(CPU)'}")
    
    return results

def benchmark_umap(sizes: List[int]) -> List[Tuple[int, float, bool, bool]]:
    """Benchmark AdaptiveUMAP with different sizes"""
    print("\n=== UMAP Benchmark ===")
    results = []
    
    for size in sizes:
        print(f"\nTesting UMAP with {size} samples")
        X = np.random.randn(size, 128).astype(np.float32)  # Smaller feature dimension for speed
        
        umap_instance = AdaptiveUMAP(n_components=2, n_neighbors=min(15, size-1), random_state=42)
        
        start_time = time.time()
        result, metrics = umap_instance.fit_transform(X)
        total_time = time.time() - start_time
        
        print(f"   ✅ UMAP: {X.shape} -> {result.shape}")
        print(f"   Time: {total_time:.3f}s")
        print(f"   CUDA enabled: {'✅' if umap_instance.cuda_enabled else '❌'}")
        print(f"   CuPy accelerated: {'✅' if umap_instance.cupy_accelerated else '❌'}")
        print(f"   Performance: {metrics}")
        
        results.append((size, total_time, umap_instance.cuda_enabled, umap_instance.cupy_accelerated))
    
    return results

def benchmark_clustering(sizes: List[int]) -> List[Tuple[int, float, float, bool, bool]]:
    """Benchmark clustering algorithms"""
    print("\n=== Clustering Benchmark ===")
    results = []
    
    for size in sizes:
        print(f"\nTesting clustering with {size} samples")
        X = np.random.randn(size, 64).astype(np.float32)  # 2D for clustering
        
        # Test DBSCAN
        dbscan = AdaptiveDBSCAN(eps=0.5, min_samples=5)
        start_time = time.time()
        labels, dbscan_metrics = dbscan.fit_predict(X)
        dbscan_time = time.time() - start_time
        n_clusters_dbscan = len(set(labels)) - (1 if -1 in labels else 0)
        
        # Test K-Means
        kmeans = AdaptiveKMeans(n_clusters=min(8, size//10), random_state=42)
        start_time = time.time()
        labels, kmeans_metrics = kmeans.fit_predict(X)
        kmeans_time = time.time() - start_time
        n_clusters_kmeans = len(set(labels))
        
        print(f"   DBSCAN: {n_clusters_dbscan} clusters in {dbscan_time:.3f}s")
        print(f"   K-Means: {n_clusters_kmeans} clusters in {kmeans_time:.3f}s")
        print(f"   DBSCAN CuPy: {'✅' if dbscan.cupy_accelerated else '❌'}")
        print(f"   K-Means CuPy: {'✅' if kmeans.cupy_accelerated else '❌'}")
        
        results.append((size, dbscan_time, kmeans_time, 
                       dbscan.cupy_accelerated, kmeans.cupy_accelerated))
    
    return results

def main():
    """Run comprehensive benchmarks"""
    
    # Test different dataset sizes
    small_sizes = [100, 500, 1000]
    medium_sizes = [1000, 2000, 5000] 
    
    print("\n" + "="*60)
    print("COMPREHENSIVE CUPY ACCELERATION BENCHMARK")
    print("="*60)
    
    # Benchmark preprocessing
    preprocessing_results = benchmark_preprocessing(small_sizes)
    
    # Benchmark UMAP (smaller sizes due to computational cost)
    umap_results = benchmark_umap([100, 500, 1000])
    
    # Benchmark clustering
    clustering_results = benchmark_clustering(medium_sizes)
    
    # Summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)
    
    print("\n📊 Preprocessing Performance:")
    for size, our_time, baseline_time, speedup in preprocessing_results:
        status = "🚀 ACCELERATED" if speedup > 1.1 else "⚡ EQUIVALENT" if speedup > 0.9 else "🐌 SLOWER"
        print(f"   {size:4d} samples: {speedup:.2f}x speedup {status}")
    
    print("\n📊 UMAP Performance:")
    for size, time_taken, cuda_enabled, cupy_accelerated in umap_results:
        accel_status = []
        if cuda_enabled:
            accel_status.append("CUDA")
        if cupy_accelerated:
            accel_status.append("CuPy")
        accel_str = "+".join(accel_status) if accel_status else "CPU"
        print(f"   {size:4d} samples: {time_taken:.2f}s ({accel_str})")
    
    print("\n📊 Clustering Performance:")
    for size, dbscan_time, kmeans_time, dbscan_cupy, kmeans_cupy in clustering_results:
        print(f"   {size:4d} samples: DBSCAN {dbscan_time:.3f}s {'(CuPy)' if dbscan_cupy else '(CPU)'}, "
              f"K-Means {kmeans_time:.3f}s {'(CuPy)' if kmeans_cupy else '(CPU)'}")
    
    # Test memory efficiency
    print("\n🔍 Memory Efficiency Test:")
    try:
        large_data = np.random.randn(10000, 256).astype(np.float32)
        print(f"   Large dataset: {large_data.shape} ({large_data.nbytes / 1024**2:.1f} MB)")
        
        # Test GPU memory transfer
        start_time = time.time()
        gpu_data = CuPyAccelerator.to_gpu(large_data)
        transfer_time = time.time() - start_time
        
        cpu_data = CuPyAccelerator.to_cpu(gpu_data)
        
        print(f"   GPU transfer: {transfer_time:.3f}s")
        print(f"   Data integrity: {'✅ OK' if np.allclose(large_data, cpu_data) else '❌ FAILED'}")
        
    except Exception as e:
        print(f"   Memory test failed: {e}")
    
    print("\n✅ CuPy acceleration benchmark completed!")
    print(f"   Environment: {'GPU-accelerated' if cp.cuda.is_available() else 'CPU-only'}")
    print(f"   Best use cases: Large dataset preprocessing, mathematical operations")
    print(f"   Fallback behavior: ✅ Graceful CPU fallback implemented")

if __name__ == "__main__":
    main()