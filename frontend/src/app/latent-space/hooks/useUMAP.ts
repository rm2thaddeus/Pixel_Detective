'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, gpuApi } from '@/lib/api';
import { UMAPProjectionResponse, ClusteringRequest, ClusterLabelRequest, UMAPPoint, ClusteringInfo } from '../types/latent-space';
import { useStore } from '@/store/useStore';

const USE_GPU_SERVICE = true; // Feature flag to easily switch between services

const fetchUMAPProjection = async (
  collection: string | null,
  sampleSize: number = 500
): Promise<UMAPProjectionResponse> => {
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
    const params: any = { sample_size: sampleSize, collection_name: collection };
    const response = await api.get(`/umap/projection`, { params });
    return response.data;
  }
};

interface ClusteringMutationVariables extends ClusteringRequest {
  points: UMAPPoint[];
}

const performClusteringOnGpu = async (
  variables: ClusteringMutationVariables,
  collection: string | null,
): Promise<UMAPProjectionResponse> => {
    const { points, ...clusteringRequest } = variables;
    // The GPU service expects data as a list of [x, y] coordinates
    const dataForApi = points.map(p => [p.x, p.y]);
  
    console.log(`🚀 Requesting clustering from GPU service with algorithm: ${clusteringRequest.algorithm}`);
    const clusterResponse = await gpuApi.post('/umap/cluster', {
      ...clusteringRequest,
      data: dataForApi,
    });

    // The GPU service returns { labels: [], silhouette_score: float, ... }
    // We need to merge this back into our original points data structure
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
};

const postClusterLabel = async (
  collection: string | null,
  labelRequest: ClusterLabelRequest
): Promise<void> => {
  const params: any = {};
  if (collection) {
    params.collection_name = collection;
  }
  
  // Assuming labeling might be a feature on the main API or GPU API
  const service = USE_GPU_SERVICE ? gpuApi : api;
  await service.post(`/umap/cluster_label`, labelRequest, { params });
};

export function useUMAP(sampleSize: number = 500) {
  const { collection } = useStore();
  const queryClient = useQueryClient();

  const basicProjection = useQuery({
    queryKey: ['umap', 'projection', collection, sampleSize],
    queryFn: () => fetchUMAPProjection(collection, sampleSize),
    enabled: !!collection, // Only run when a collection is selected
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  const clusteringMutation = useMutation({
    mutationFn: (request: ClusteringMutationVariables) => 
      performClusteringOnGpu(request, collection),
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