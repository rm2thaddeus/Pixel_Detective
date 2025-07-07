'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, gpuApi } from '@/lib/api';
import { UMAPProjectionResponse, ClusteringRequest, ClusterLabelRequest, UMAPPoint, ClusteringInfo } from '../types/latent-space';
import { useStore } from '@/store/useStore';

// We prefer the GPU micro-service if it is reachable. We lazily probe its /health
// endpoint exactly once per page load, then cache the result.
let USE_GPU_CLUSTER = true;
let gpuHealthChecked = false;

/**
 * Probe the GPU-accelerated UMAP service and dynamically pick the first
 * reachable base URL.  This allows developers to run the service either via
 * Docker Compose (host port 8003) **or** by launching Uvicorn directly on the
 * host (default 8001) without touching env vars – the front-end adapts at run
 * time.  The chosen URL is cached for the remainder of the session so that
 * React Query keys stay stable.
 */
async function ensureGpuServiceHealthy(): Promise<boolean> {
  if (gpuHealthChecked) return USE_GPU_CLUSTER;
  gpuHealthChecked = true;

  // Candidate base URLs in order of preference.  The environment variable can
  // always override hard-coded defaults.
  const candidateBases: string[] = [
    process.env.NEXT_PUBLIC_GPU_API_URL as string | undefined,
    'http://localhost:8003', // Docker-Compose default mapping
    'http://localhost:8001', // Local "uvicorn main:app --port 8001" dev
    'http://host.docker.internal:8003',
    'http://host.docker.internal:8001',
  ].filter(Boolean) as string[];

  for (const base of candidateBases) {
    try {
      const res = await gpuApi.get(`${base}/health`, { timeout: 3000 });
      if (res.status === 200) {
        // Point the shared Axios instance at the working base so subsequent
        // requests automatically use the correct origin.
        gpuApi.defaults.baseURL = base;
        USE_GPU_CLUSTER = true;
        console.info(`[useUMAP] ✅ GPU UMAP service detected at ${base}`);
        return true;
      }
    } catch {
      // Silent – we will try next candidate
    }
  }

  console.warn('[useUMAP] ⚠️  GPU UMAP service not reachable on any known port. Falling back to CPU clustering.');
  USE_GPU_CLUSTER = false;
  return false;
}

const fetchUMAPProjection = async (
  collection: string | null,
  sampleSize: number = 500
): Promise<UMAPProjectionResponse> => {
  console.log(`🔍 fetchUMAPProjection called with collection: ${collection}, sampleSize: ${sampleSize}`);
  
  if (!collection) {
    throw new Error("A collection must be selected to compute UMAP projections.");
  }
  
  console.log(`🌐 Requesting UMAP projection from main backend, sample_size: ${sampleSize}`);
  const params = { sample_size: sampleSize };
  const response = await api.get(`/umap/projection`, { params, timeout: 30000 });
  console.log(`✅ UMAP projection response received:`, {
    status: response.status,
    pointsCount: response.data?.points?.length,
    collection: response.data?.collection,
    firstPoint: response.data?.points?.[0],
    samplePoints: response.data?.points?.slice(0, 3),
  });
  return response.data;
};

interface ClusteringMutationVariables extends ClusteringRequest {
  points: UMAPPoint[];
}

const performClustering = async (
  variables: ClusteringMutationVariables,
  collection: string | null,
): Promise<UMAPProjectionResponse> => {
  if (await ensureGpuServiceHealthy()) {
    // GPU service clustering (existing logic)
    const { points, ...clusteringRequest } = variables;
    const dataForApi = points.map(p => [p.x, p.y]);
  
    try {
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

      const clustersMap = clusterResponse.data.clusters || undefined;

      const newClusteringInfo: ClusteringInfo = {
        algorithm: clusteringRequest.algorithm,
        n_clusters: clustersMap ? Object.keys(clustersMap).length : Math.max(...clusterResponse.data.labels) + 1,
        silhouette_score: clusterResponse.data.silhouette_score,
        n_outliers: clusterResponse.data.labels.filter((l: number) => l === -1).length,
        parameters: {
          ...clusteringRequest,
        },
        clusters: clustersMap,
      };

      return {
        points: newPoints,
        collection: collection || 'unknown',
        clustering_info: newClusteringInfo,
      };
    } catch (err: any) {
      if (err?.response) {
        console.warn('❌ GPU clustering failed:', {
          status: err.response.status,
          data: err.response.data,
        });
      } else {
        console.warn('❌ GPU clustering failed (no response object):', err);
      }
      console.info('🔁 Falling back to main backend clustering endpoint...');
      // Fall back to main backend clustering endpoint
    }
  }

  // ---------- Fallback to main backend --------------
  const { points, ...clusteringRequest } = variables;
  console.log(`🌐 Requesting clustering from main backend with algorithm: ${clusteringRequest.algorithm}`);
  try {
    const response = await api.post('/umap/projection_with_clustering', clusteringRequest, {
      params: { sample_size: points.length },
      timeout: 30000
    });
    console.log(`✅ Clustering response received from fallback:`, response.data);
    return response.data;
  } catch (err: any) {
    console.warn('[useUMAP] Clustering fallback failed:', err);
    // Fallback to projection-only data so the UI can render without clustering
    return { points: variables.points, collection: collection || 'unknown', clustering_info: undefined };
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
  const service = await ensureGpuServiceHealthy() ? gpuApi : api;
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
    error: basicProjection.error,
  };
} 