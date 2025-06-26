"""
Benchmark script to compare CPU vs CUDA performance.
"""
import time
import numpy as np
from typing import Dict, Any

def benchmark_umap(data_sizes: list, n_features: int = 512) -> Dict[str, Any]:
    """Benchmark UMAP performance across different data sizes."""
    
    results = {
        "data_sizes": data_sizes,
        "cpu_times": [],
        "cuda_times": [],
        "speedups": []
    }
    
    for n_samples in data_sizes:
        print(f"Benchmarking {n_samples} samples...")
        
        # Generate synthetic data
        X = np.random.rand(n_samples, n_features).astype(np.float32)
        
        # CPU benchmark
        import umap
        cpu_reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42)
        start_time = time.time()
        cpu_result = cpu_reducer.fit_transform(X)
        cpu_time = time.time() - start_time
        results["cpu_times"].append(cpu_time)
        
        # CUDA benchmark
        try:
            from cuml.manifold import UMAP as cuUMAP
            cuda_reducer = cuUMAP(n_components=2, metric="cosine", random_state=42)
            start_time = time.time()
            cuda_result = cuda_reducer.fit_transform(X)
            cuda_time = time.time() - start_time
            results["cuda_times"].append(cuda_time)
            
            speedup = cpu_time / cuda_time
            results["speedups"].append(speedup)
            
            print(f"  CPU: {cpu_time:.2f}s, CUDA: {cuda_time:.2f}s, Speedup: {speedup:.2f}x")
            
        except ImportError:
            print("  cuML not available, skipping CUDA benchmark")
            results["cuda_times"].append(None)
            results["speedups"].append(None)
    
    return results

def benchmark_clustering(data_sizes: list, n_features: int = 512) -> Dict[str, Any]:
    """Benchmark clustering performance across different data sizes."""
    
    results = {
        "algorithms": ["DBSCAN", "KMeans"],
        "data_sizes": data_sizes,
        "cpu_times": {"DBSCAN": [], "KMeans": []},
        "cuda_times": {"DBSCAN": [], "KMeans": []},
        "speedups": {"DBSCAN": [], "KMeans": []}
    }
    
    for n_samples in data_sizes:
        print(f"Benchmarking clustering with {n_samples} samples...")
        
        # Generate 2D data for clustering (similar to UMAP output)
        X = np.random.rand(n_samples, 2).astype(np.float32)
        
        # DBSCAN Benchmark
        print("  DBSCAN...")
        from sklearn.cluster import DBSCAN
        cpu_clusterer = DBSCAN(eps=0.3, min_samples=5)
        start_time = time.time()
        cpu_labels = cpu_clusterer.fit_predict(X)
        cpu_time = time.time() - start_time
        results["cpu_times"]["DBSCAN"].append(cpu_time)
        
        try:
            from cuml.cluster import DBSCAN as cuDBSCAN
            cuda_clusterer = cuDBSCAN(eps=0.3, min_samples=5)
            start_time = time.time()
            cuda_labels = cuda_clusterer.fit_predict(X)
            cuda_time = time.time() - start_time
            results["cuda_times"]["DBSCAN"].append(cuda_time)
            
            speedup = cpu_time / cuda_time
            results["speedups"]["DBSCAN"].append(speedup)
            print(f"    CPU: {cpu_time:.2f}s, CUDA: {cuda_time:.2f}s, Speedup: {speedup:.2f}x")
            
        except ImportError:
            print("    cuML DBSCAN not available")
            results["cuda_times"]["DBSCAN"].append(None)
            results["speedups"]["DBSCAN"].append(None)
        
        # K-Means Benchmark
        print("  K-Means...")
        from sklearn.cluster import KMeans
        cpu_clusterer = KMeans(n_clusters=5, random_state=42)
        start_time = time.time()
        cpu_labels = cpu_clusterer.fit_predict(X)
        cpu_time = time.time() - start_time
        results["cpu_times"]["KMeans"].append(cpu_time)
        
        try:
            from cuml.cluster import KMeans as cuKMeans
            cuda_clusterer = cuKMeans(n_clusters=5, random_state=42)
            start_time = time.time()
            cuda_labels = cuda_clusterer.fit_predict(X)
            cuda_time = time.time() - start_time
            results["cuda_times"]["KMeans"].append(cuda_time)
            
            speedup = cpu_time / cuda_time
            results["speedups"]["KMeans"].append(speedup)
            print(f"    CPU: {cpu_time:.2f}s, CUDA: {cuda_time:.2f}s, Speedup: {speedup:.2f}x")
            
        except ImportError:
            print("    cuML K-Means not available")
            results["cuda_times"]["KMeans"].append(None)
            results["speedups"]["KMeans"].append(None)
    
    return results

if __name__ == "__main__":
    print("CUDA Performance Benchmark")
    print("=" * 50)
    
    # Test with different data sizes
    sizes = [100, 500, 1000, 5000]
    
    print("\n1. UMAP Benchmark")
    print("-" * 30)
    umap_results = benchmark_umap(sizes)
    
    print("\nUMAP Benchmark Results:")
    for i, size in enumerate(sizes):
        cpu_time = umap_results["cpu_times"][i]
        cuda_time = umap_results["cuda_times"][i]
        speedup = umap_results["speedups"][i]
        
        if cuda_time is not None:
            print(f"{size:5d} samples: {cpu_time:6.2f}s → {cuda_time:6.2f}s ({speedup:5.2f}x speedup)")
        else:
            print(f"{size:5d} samples: {cpu_time:6.2f}s (CUDA not available)")
    
    print("\n2. Clustering Benchmark")
    print("-" * 30)
    clustering_results = benchmark_clustering(sizes)
    
    print("\nClustering Benchmark Results:")
    for algorithm in ["DBSCAN", "KMeans"]:
        print(f"\n{algorithm}:")
        for i, size in enumerate(sizes):
            cpu_time = clustering_results["cpu_times"][algorithm][i]
            cuda_time = clustering_results["cuda_times"][algorithm][i]
            speedup = clustering_results["speedups"][algorithm][i]
            
            if cuda_time is not None:
                print(f"  {size:5d} samples: {cpu_time:6.2f}s → {cuda_time:6.2f}s ({speedup:5.2f}x speedup)")
            else:
                print(f"  {size:5d} samples: {cpu_time:6.2f}s (CUDA not available)")
    
    print("\n" + "=" * 50)
    print("Benchmark completed!") 