import { create } from 'zustand';
import { UMAPProjectionResponse, ClusteringRequest, ViewportTransform } from '../types/latent-space';
import { ColorPaletteName } from '../utils/visualization';

interface LatentSpaceState {
  // Data state
  projectionData: UMAPProjectionResponse | null;
  selectedCluster: number | null;
  clusterLabels: Record<number, string>; // To hold user-defined labels
  clusteringParams: ClusteringRequest;
  isLoading: boolean;
  viewportTransform: ViewportTransform;
  
  // Visualization settings
  colorPalette: ColorPaletteName;
  showOutliers: boolean;
  pointSize: number;
  
  // Actions
  setProjectionData: (data: UMAPProjectionResponse | null) => void;
  setSelectedCluster: (clusterId: number | null) => void;
  updateClusteringParams: (params: Partial<ClusteringRequest>) => void;
  setLoading: (loading: boolean) => void;
  updateViewport: (transform: ViewportTransform) => void;
  setClusterLabel: (clusterId: number, label: string) => void;
  
  // Visualization actions
  setColorPalette: (palette: ColorPaletteName) => void;
  setShowOutliers: (show: boolean) => void;
  setPointSize: (size: number) => void;
  
  // Reset function
  resetState: () => void;
}

const initialState = {
  projectionData: null,
  selectedCluster: null,
  clusterLabels: {},
  clusteringParams: {
    algorithm: 'dbscan' as const,
    eps: 0.5,
    min_samples: 5,
  },
  isLoading: false,
  viewportTransform: { x: 0, y: 0, scale: 1 },
  colorPalette: 'observable' as ColorPaletteName,
  showOutliers: true,
  pointSize: 10,
};

export const useLatentSpaceStore = create<LatentSpaceState>((set, get) => ({
  ...initialState,
  
  setProjectionData: (data) => {
    console.log('🗃️ Setting projection data:', {
      hasData: !!data,
      pointsCount: data?.points?.length,
      collection: data?.collection,
      firstPoint: data?.points?.[0],
      samplePoints: data?.points?.slice(0, 3),
    });
    set({ 
      projectionData: data, 
      clusterLabels: {}, // Reset labels on new data
      selectedCluster: null, // Reset selection on new data
    });
  },
  
  setSelectedCluster: (clusterId) => {
    console.log('🎯 Setting selected cluster:', clusterId);
    set({ selectedCluster: clusterId });
  },
  
  updateClusteringParams: (params) => {
    const currentParams = get().clusteringParams;
    const newParams = { ...currentParams, ...params };
    console.log('⚙️ Updating clustering params:', newParams);
    set({ clusteringParams: newParams });
  },
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  updateViewport: (transform) => set({ viewportTransform: transform }),
  
  setClusterLabel: (clusterId, label) => {
    const currentLabels = get().clusterLabels;
    console.log('🏷️ Setting cluster label:', clusterId, '→', label);
    set({
      clusterLabels: { ...currentLabels, [clusterId]: label },
    });
  },
  
  setColorPalette: (palette) => {
    console.log('🎨 Setting color palette:', palette);
    set({ colorPalette: palette });
  },
  
  setShowOutliers: (show) => {
    console.log('👁️ Setting show outliers:', show);
    set({ showOutliers: show });
  },
  
  setPointSize: (size) => {
    console.log('📏 Setting point size:', size);
    set({ pointSize: size });
  },
  
  resetState: () => {
    console.log('🔄 Resetting latent space state');
    set(initialState);
  },
})); 