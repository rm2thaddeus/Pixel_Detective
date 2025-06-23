'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, gpuApi } from '@/lib/api';
import { UMAPProjectionResponse, ClusteringRequest, ClusterLabelRequest, UMAPPoint, ClusteringInfo } from '../types/latent-space';
import { useStore } from '@/store/useStore';

const USE_GPU_SERVICE = false; // Feature flag to easily switch between services - CHANGED TO FALSE

const fetchUMAPProjection = async (
  collection: string | null,
  sampleSize: number = 500
): Promise<UMAPProjectionResponse> => {
  console.log(`🔍 fetchUMAPProjection called with collection: ${collection}, sampleSize: ${sampleSize}`);
  
  if (!collection) {
    throw new Error("A collection must be selected to compute UMAP projections.");
  }
  
  if (USE_GPU_SERVICE) {
    console.log(`🚀 Requesting UMAP projection from GPU service for collection: ${collection}`);
    const response = await gpuApi.post(`/umap/projection`, { 
      collection_name: collection,
      sample_size: sampleSize,
    });
    return response.data;
  } else {
    console.log(`🌐 Requesting UMAP projection from main backend, sample_size: ${sampleSize}`);
    // The backend uses the globally selected collection, not a parameter
    const params = { sample_size: sampleSize };
    const response = await api.get(`/umap/projection`, { params });
    console.log(`✅ UMAP projection response received:`, {
      status: response.status,
      pointsCount: response.data?.points?.length,
      collection: response.data?.collection,
      firstPoint: response.data?.points?.[0],
      samplePoints: response.data?.points?.slice(0, 3),
    });
    return response.data;
  }
};

interface ClusteringMutationVariables extends ClusteringRequest {
  points: UMAPPoint[];
}

const performClustering = async (
  variables: ClusteringMutationVariables,
  collection: string | null,
): Promise<UMAPProjectionResponse> => {
  if (USE_GPU_SERVICE) {
    // GPU service clustering (existing logic)
    const { points, ...clusteringRequest } = variables;
    const dataForApi = points.map(p => [p.x, p.y]);
  
    console.log(`🚀 Requesting clustering from GPU service with algorithm: ${clusteringRequest.algorithm}`);
    const clusterResponse = await gpuApi.post('/umap/cluster', {
      ...clusteringRequest,
      data: dataForApi,
    });

    const newPoints = points.map((point, index) => ({
      ...point,
      cluster_id: clusterResponse.data.labels[index],
      is_outlier: clusterResponse.data.labels[index] === -1,
    }));

    const newClusteringInfo: ClusteringInfo = {
      algorithm: clusteringRequest.algorithm,
      n_clusters: Math.max(...clusterResponse.data.labels) + 1,
      silhouette_score: clusterResponse.data.silhouette_score,
      n_outliers: clusterResponse.data.labels.filter((l: number) => l === -1).length,
      parameters: {
        ...clusteringRequest,
      }
    };

    return {
      points: newPoints,
      collection: collection || 'unknown',
      clustering_info: newClusteringInfo,
    };
  } else {
    // Main backend clustering
    const { points, ...clusteringRequest } = variables;
    console.log(`🌐 Requesting clustering from main backend with algorithm: ${clusteringRequest.algorithm}`);
    
    const response = await api.post('/umap/projection_with_clustering', clusteringRequest, {
      params: { sample_size: points.length }
    });
    
    console.log(`✅ Clustering response received:`, response.data);
    return response.data;
  }
};

const postClusterLabel = async (
  collection: string | null,
  labelRequest: ClusterLabelRequest
): Promise<void> => {
      const params: Record<string, string> = {};
    if (collection) {
      params.collection_name = collection;
    }
  
  // Assuming labeling might be a feature on the main API or GPU API
  const service = USE_GPU_SERVICE ? gpuApi : api;
  await service.post(`/umap/cluster_label`, labelRequest, { params });
};

export function useUMAP(sampleSize: number = 500) {
  const { collection } = useStore();

  const basicProjection = useQuery({
    queryKey: ['umap', 'projection', collection, sampleSize],
    queryFn: () => fetchUMAPProjection(collection, sampleSize),
    enabled: !!collection, // Only run when a collection is selected
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  const clusteringMutation = useMutation({
    mutationFn: (request: ClusteringMutationVariables) => 
      performClustering(request, collection),
    // onSuccess is handled in the component to update the Zustand store
  });

  const labelMutation = useMutation({
    mutationFn: (request: ClusterLabelRequest) =>
      postClusterLabel(collection, request),
    onSuccess: () => {
      // Optionally invalidate or update queries if labels are fetched from backend
      // For now, client-side state is updated instantly.
    },
  });

  return {
    basicProjection,
    clusteringMutation,
    labelMutation,
    isLoading: basicProjection.isLoading && basicProjection.isFetching,
    error: basicProjection.error || clusteringMutation.error,
  };
} 