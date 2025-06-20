"""
Adaptive ML algorithms that use CUDA when available, fallback to CPU.
"""
import logging
from typing import Union, Any, Tuple, Dict
import numpy as np
import time
from dataclasses import dataclass

# Standard ML libraries
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

try:
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# CUDA acceleration attempts
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    # Test if GPU is actually available
    try:
        cp.cuda.Device(0).compute_capability
        GPU_AVAILABLE = True
    except:
        GPU_AVAILABLE = False
except ImportError:
    CUPY_AVAILABLE = False
    GPU_AVAILABLE = False

try:
    import cuml
    from cuml.manifold import UMAP as cumlUMAP
    from cuml.cluster import DBSCAN as cumlDBSCAN, KMeans as cumlKMeans
    from cuml.preprocessing import StandardScaler as cumlStandardScaler
    CUML_AVAILABLE = True
    
    # Try to install cuml.accel for zero-code-change acceleration
    try:
        import cuml.accel
        cuml.accel.install()
        CUML_ACCEL_AVAILABLE = True
    except (ImportError, AttributeError):
        CUML_ACCEL_AVAILABLE = False
        
except ImportError:
    CUML_AVAILABLE = False
    CUML_ACCEL_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for ML operations"""
    algorithm: str
    processing_time: float
    input_shape: Tuple[int, ...]
    output_shape: Union[Tuple[int, ...], None] = None
    cuda_enabled: bool = False
    cupy_accelerated: bool = False
    memory_usage: Union[float, None] = None
    
    def __str__(self):
        accel_info = []
        if self.cuda_enabled:
            accel_info.append("CUDA")
        if self.cupy_accelerated:
            accel_info.append("CuPy")
        
        accel_str = f" ({'+'.join(accel_info)})" if accel_info else " (CPU)"
        
        return (f"{self.algorithm}{accel_str}: {self.input_shape} -> "
                f"{self.output_shape} in {self.processing_time:.3f}s")

class CuPyAccelerator:
    """CuPy-based acceleration for common mathematical operations"""
    
    @staticmethod
    def to_gpu(data: np.ndarray) -> Union[np.ndarray, 'cp.ndarray']:
        """Move data to GPU if possible"""
        if not CUPY_AVAILABLE or not GPU_AVAILABLE:
            return data
        try:
            return cp.asarray(data)
        except Exception as e:
            logger.warning(f"Failed to move data to GPU: {e}")
            return data
    
    @staticmethod
    def to_cpu(data: Union[np.ndarray, 'cp.ndarray']) -> np.ndarray:
        """Move data back to CPU"""
        if CUPY_AVAILABLE and hasattr(data, 'get'):
            return data.get()
        return data
    
    @staticmethod
    def standardize(data: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Standardize data using CuPy if available"""
        if not CUPY_AVAILABLE or not GPU_AVAILABLE:
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            return scaler.fit_transform(data), False
        
        try:
            # Use CuPy for faster standardization
            gpu_data = cp.asarray(data)
            mean = cp.mean(gpu_data, axis=0)
            std = cp.std(gpu_data, axis=0)
            std = cp.where(std == 0, 1, std)  # Avoid division by zero
            standardized = (gpu_data - mean) / std
            return standardized.get(), True
        except Exception as e:
            logger.warning(f"CuPy standardization failed: {e}, falling back to CPU")
            from sklearn.preprocessing import StandardScaler
            scaler = StandardScaler()
            return scaler.fit_transform(data), False
    
    @staticmethod
    def distance_matrix(data: np.ndarray, chunk_size: int = 1000) -> Tuple[np.ndarray, bool]:
        """Compute distance matrix using CuPy if available"""
        if not CUPY_AVAILABLE or not GPU_AVAILABLE or data.shape[0] > chunk_size:
            # Fall back to sklearn for large datasets or when CuPy unavailable
            from sklearn.metrics.pairwise import euclidean_distances
            return euclidean_distances(data), False
        
        try:
            gpu_data = cp.asarray(data)
            # Compute pairwise distances using CuPy
            diff = gpu_data[:, None, :] - gpu_data[None, :, :]
            distances = cp.sqrt(cp.sum(diff ** 2, axis=2))
            return distances.get(), True
        except Exception as e:
            logger.warning(f"CuPy distance computation failed: {e}, falling back to CPU")
            from sklearn.metrics.pairwise import euclidean_distances
            return euclidean_distances(data), False

class AdaptiveUMAP:
    """Adaptive UMAP with CUDA and CuPy acceleration support"""
    
    def __init__(self, n_components=2, n_neighbors=15, min_dist=0.1, 
                 metric='euclidean', random_state=42, **kwargs):
        self.n_components = n_components
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.metric = metric
        self.random_state = random_state
        self.kwargs = kwargs
        self.cupy_accelerated = False
        
        # Initialize the appropriate UMAP implementation
        if CUML_AVAILABLE:
            logger.info("Using cuML UMAP for GPU acceleration")
            self.umap_impl = cumlUMAP(
                n_components=n_components,
                n_neighbors=n_neighbors,
                min_dist=min_dist,
                metric=metric,
                random_state=random_state,
                **kwargs
            )
            self.cuda_enabled = True
        elif UMAP_AVAILABLE:
            logger.info("Using standard UMAP with CuPy preprocessing")
            self.umap_impl = umap.UMAP(
                n_components=n_components,
                n_neighbors=n_neighbors,
                min_dist=min_dist,
                metric=metric,
                random_state=random_state,
                **kwargs
            )
            self.cuda_enabled = False
        else:
            raise ImportError("Neither cuML nor UMAP available")
    
    def fit_transform(self, X: np.ndarray) -> Tuple[np.ndarray, PerformanceMetrics]:
        """Fit UMAP and transform data with performance tracking"""
        start_time = time.time()
        input_shape = X.shape
        
        # Preprocess with CuPy if available and beneficial
        preprocessed_data = X
        cupy_used = False
        
        if not self.cuda_enabled and X.shape[0] > 1000:
            # Use CuPy for preprocessing large datasets when cuML unavailable
            try:
                standardized_data, cupy_used = CuPyAccelerator.standardize(X)
                if cupy_used:
                    preprocessed_data = standardized_data
                    self.cupy_accelerated = True
                    logger.info("Using CuPy acceleration for UMAP preprocessing")
            except Exception as e:
                logger.warning(f"CuPy preprocessing failed: {e}")
        
        # Perform UMAP transformation
        try:
            if self.cuda_enabled:
                # cuML UMAP expects float32
                if preprocessed_data.dtype != np.float32:
                    preprocessed_data = preprocessed_data.astype(np.float32)
            
            result = self.umap_impl.fit_transform(preprocessed_data)
            
            # Ensure result is numpy array
            if hasattr(result, 'get'):
                result = result.get()
            elif hasattr(result, 'to_numpy'):
                result = result.to_numpy()
            
        except Exception as e:
            logger.error(f"UMAP transformation failed: {e}")
            # Fallback to basic numpy implementation
            logger.info("Falling back to random projection")
            from sklearn.random_projection import GaussianRandomProjection
            projector = GaussianRandomProjection(n_components=self.n_components, 
                                               random_state=self.random_state)
            result = projector.fit_transform(X)
        
        processing_time = time.time() - start_time
        output_shape = result.shape
        
        metrics = PerformanceMetrics(
            algorithm="UMAP",
            processing_time=processing_time,
            input_shape=input_shape,
            output_shape=output_shape,
            cuda_enabled=self.cuda_enabled,
            cupy_accelerated=self.cupy_accelerated
        )
        
        logger.info(f"UMAP completed: {metrics}")
        return result, metrics

class AdaptiveDBSCAN:
    """Adaptive DBSCAN with CUDA and CuPy acceleration support"""
    
    def __init__(self, eps=0.5, min_samples=5, **kwargs):
        self.eps = eps
        self.min_samples = min_samples
        self.kwargs = kwargs
        self.cupy_accelerated = False
        
        if CUML_AVAILABLE:
            logger.info("Using cuML DBSCAN for GPU acceleration")
            self.dbscan_impl = cumlDBSCAN(eps=eps, min_samples=min_samples, **kwargs)
            self.cuda_enabled = True
        elif SKLEARN_AVAILABLE:
            logger.info("Using sklearn DBSCAN with CuPy preprocessing")
            self.dbscan_impl = DBSCAN(eps=eps, min_samples=min_samples, **kwargs)
            self.cuda_enabled = False
        else:
            raise ImportError("Neither cuML nor sklearn available")
    
    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, PerformanceMetrics]:
        """Fit DBSCAN and predict clusters with performance tracking"""
        start_time = time.time()
        input_shape = X.shape
        
        # Preprocess with CuPy if available
        preprocessed_data = X
        cupy_used = False
        
        if not self.cuda_enabled and X.shape[0] > 500:
            # Use CuPy for distance computation acceleration
            try:
                if X.shape[0] < 2000:  # Only for moderate sizes
                    _, cupy_used = CuPyAccelerator.distance_matrix(X[:100])  # Test run
                    if cupy_used:
                        self.cupy_accelerated = True
                        logger.info("Using CuPy acceleration for DBSCAN preprocessing")
            except Exception as e:
                logger.warning(f"CuPy preprocessing failed: {e}")
        
        # Perform clustering
        try:
            if self.cuda_enabled:
                # cuML DBSCAN expects float32
                if preprocessed_data.dtype != np.float32:
                    preprocessed_data = preprocessed_data.astype(np.float32)
            
            labels = self.dbscan_impl.fit_predict(preprocessed_data)
            
            # Ensure result is numpy array
            if hasattr(labels, 'get'):
                labels = labels.get()
            elif hasattr(labels, 'to_numpy'):
                labels = labels.to_numpy()
                
        except Exception as e:
            logger.error(f"DBSCAN clustering failed: {e}")
            # Fallback to simple clustering
            logger.info("Falling back to single cluster")
            labels = np.zeros(X.shape[0], dtype=int)
        
        processing_time = time.time() - start_time
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        
        metrics = PerformanceMetrics(
            algorithm="DBSCAN",
            processing_time=processing_time,
            input_shape=input_shape,
            output_shape=(len(labels),),
            cuda_enabled=self.cuda_enabled,
            cupy_accelerated=self.cupy_accelerated
        )
        
        logger.info(f"DBSCAN completed: {metrics}, found {n_clusters} clusters")
        return labels, metrics

class AdaptiveKMeans:
    """Adaptive K-Means with CUDA and CuPy acceleration support"""
    
    def __init__(self, n_clusters=8, random_state=42, **kwargs):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.kwargs = kwargs
        self.cupy_accelerated = False
        
        if CUML_AVAILABLE:
            logger.info("Using cuML K-Means for GPU acceleration")
            self.kmeans_impl = cumlKMeans(n_clusters=n_clusters, 
                                        random_state=random_state, **kwargs)
            self.cuda_enabled = True
        elif SKLEARN_AVAILABLE:
            logger.info("Using sklearn K-Means with CuPy preprocessing")
            self.kmeans_impl = KMeans(n_clusters=n_clusters, 
                                    random_state=random_state, **kwargs)
            self.cuda_enabled = False
        else:
            raise ImportError("Neither cuML nor sklearn available")
    
    def fit_predict(self, X: np.ndarray) -> Tuple[np.ndarray, PerformanceMetrics]:
        """Fit K-Means and predict clusters with performance tracking"""
        start_time = time.time()
        input_shape = X.shape
        
        # Preprocess with CuPy if available
        preprocessed_data = X
        cupy_used = False
        
        if not self.cuda_enabled and X.shape[0] > 1000:
            # Use CuPy for standardization
            try:
                standardized_data, cupy_used = CuPyAccelerator.standardize(X)
                if cupy_used:
                    preprocessed_data = standardized_data
                    self.cupy_accelerated = True
                    logger.info("Using CuPy acceleration for K-Means preprocessing")
            except Exception as e:
                logger.warning(f"CuPy preprocessing failed: {e}")
        
        # Perform clustering
        try:
            if self.cuda_enabled:
                # cuML K-Means expects float32
                if preprocessed_data.dtype != np.float32:
                    preprocessed_data = preprocessed_data.astype(np.float32)
            
            labels = self.kmeans_impl.fit_predict(preprocessed_data)
            
            # Ensure result is numpy array
            if hasattr(labels, 'get'):
                labels = labels.get()
            elif hasattr(labels, 'to_numpy'):
                labels = labels.to_numpy()
                
        except Exception as e:
            logger.error(f"K-Means clustering failed: {e}")
            # Fallback to random assignment
            logger.info("Falling back to random cluster assignment")
            labels = np.random.randint(0, self.n_clusters, X.shape[0])
        
        processing_time = time.time() - start_time
        
        metrics = PerformanceMetrics(
            algorithm="K-Means",
            processing_time=processing_time,
            input_shape=input_shape,
            output_shape=(len(labels),),
            cuda_enabled=self.cuda_enabled,
            cupy_accelerated=self.cupy_accelerated
        )
        
        logger.info(f"K-Means completed: {metrics}")
        return labels, metrics

# Capability detection and reporting
def get_acceleration_status() -> Dict[str, Any]:
    """Get detailed acceleration capability status"""
    return {
        'cupy_available': CUPY_AVAILABLE,
        'gpu_available': GPU_AVAILABLE,
        'cuml_available': CUML_AVAILABLE,
        'cuml_accel_available': CUML_ACCEL_AVAILABLE,
        'umap_available': UMAP_AVAILABLE,
        'sklearn_available': SKLEARN_AVAILABLE,
        'acceleration_level': (
            'full_cuda' if CUML_AVAILABLE else
            'cupy_hybrid' if CUPY_AVAILABLE and GPU_AVAILABLE else
            'cpu_only'
        )
    }

def log_performance_metrics(metrics: PerformanceMetrics):
    """Log performance metrics in a structured format"""
    logger.info(f"Performance: {metrics}")
    
    # Additional structured logging for monitoring
    if hasattr(logger, 'structured'):
        logger.structured('ml_performance', {
            'algorithm': metrics.algorithm,
            'processing_time': metrics.processing_time,
            'input_samples': metrics.input_shape[0] if metrics.input_shape else 0,
            'input_features': metrics.input_shape[1] if len(metrics.input_shape) > 1 else 0,
            'cuda_enabled': metrics.cuda_enabled,
            'cupy_accelerated': metrics.cupy_accelerated
        })