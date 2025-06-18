import { create } from 'zustand';
import { UMAPProjectionResponse, ClusteringRequest, ViewportTransform } from '../types/latent-space';

interface LatentSpaceState {
  projectionData: UMAPProjectionResponse | null;
  selectedCluster: number | null;
  clusterLabels: Record<number, string>; // To hold user-defined labels
  clusteringParams: ClusteringRequest;
  isLoading: boolean;
  viewportTransform: ViewportTransform;
  
  // Actions
  setProjectionData: (data: UMAPProjectionResponse | null) => void;
  setSelectedCluster: (clusterId: number | null) => void;
  updateClusteringParams: (params: Partial<ClusteringRequest>) => void;
  setLoading: (loading: boolean) => void;
  updateViewport: (transform: ViewportTransform) => void;
  setClusterLabel: (clusterId: number, label: string) => void;
}

export const useLatentSpaceStore = create<LatentSpaceState>((set) => ({
  projectionData: null,
  selectedCluster: null,
  clusterLabels: {},
  clusteringParams: {
    algorithm: 'dbscan',
    eps: 0.5,
    min_samples: 5,
  },
  isLoading: false,
  viewportTransform: { x: 0, y: 0, scale: 1 },
  
  setProjectionData: (data) => set({ projectionData: data, clusterLabels: {} }), // Reset labels on new data
  setSelectedCluster: (clusterId) => set({ selectedCluster: clusterId }),
  updateClusteringParams: (params) => 
    set((state) => ({ 
      clusteringParams: { ...state.clusteringParams, ...params }
    })),
  setLoading: (loading) => set({ isLoading: loading }),
  updateViewport: (transform) => set({ viewportTransform: transform }),
  setClusterLabel: (clusterId, label) =>
    set((state) => ({
      clusterLabels: { ...state.clusterLabels, [clusterId]: label },
    })),
})); 