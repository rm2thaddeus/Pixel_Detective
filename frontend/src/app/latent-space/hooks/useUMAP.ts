import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { UMAPProjectionResponse, ClusteringRequest, ClusterLabelRequest } from '../types/latent-space';
import { useStore } from '@/store/useStore';

const fetchUMAPProjection = async (
  collection: string | null,
  sampleSize: number = 500
): Promise<UMAPProjectionResponse> => {
  const params: any = { sample_size: sampleSize };
  if (collection) {
    params.collection_name = collection;
  }
  
  const response = await api.get(`/umap/projection`, { params });
  return response.data;
};

const fetchUMAPWithClustering = async (
  collection: string | null,
  clusteringRequest: ClusteringRequest,
  sampleSize: number = 500
): Promise<UMAPProjectionResponse> => {
  const params: any = { sample_size: sampleSize };
  if (collection) {
    params.collection_name = collection;
  }
  
  const response = await api.post(`/umap/projection_with_clustering`, clusteringRequest, { params });
  return response.data;
};

const postClusterLabel = async (
  collection: string | null,
  labelRequest: ClusterLabelRequest
): Promise<void> => {
  const params: any = {};
  if (collection) {
    params.collection_name = collection;
  }
  
  await api.post(`/umap/cluster_label`, labelRequest, { params });
};

export function useUMAP(sampleSize: number = 500) {
  const { collection } = useStore();
  const queryClient = useQueryClient();

  const basicProjection = useQuery({
    queryKey: ['umap', 'projection', collection, sampleSize],
    queryFn: () => fetchUMAPProjection(collection, sampleSize),
    enabled: true, // Always enabled - works without collection
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const clusteringMutation = useMutation({
    mutationFn: (request: ClusteringRequest) => 
      fetchUMAPWithClustering(collection, request, sampleSize),
    onSuccess: (data) => {
      queryClient.setQueryData(['umap', 'projection', collection, sampleSize], data);
    },
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
    isLoading: basicProjection.isLoading || clusteringMutation.isPending,
    error: basicProjection.error || clusteringMutation.error,
  };
} 