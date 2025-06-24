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
  
  // === Density overlay & selection ===
  heatmapVisible: boolean; // Toggle for 2-D density overlay
  heatmapOpacity: number;  // 0-100 percentage for overlay opacity
  selectedIds: string[];   // Hand-drawn polygon selection
  
  // Cluster polygons (convex hulls)
  clusterPolygons: Record<number, [number, number][]>; // cluster_id → hull coords
  
  // Overlay mode settings
  overlayMode: 'none' | 'heatmap' | 'terrain';
  terrainResolution: number; // cell size for contour grid
  terrainBands: number; // number of contour levels
  
  // Layer toggles
  showScatter: boolean;
  showHulls: boolean;
  showVoronoi: boolean;
  
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
  
  // Density overlay & selection actions
  setHeatmap: (v: boolean) => void;
  setHeatmapOpacity: (x: number) => void;
  setSelectedIds: (ids: string[]) => void;
  
  // Reset function
  resetState: () => void;
  
  // ===== Overlay settings =====
  setOverlayMode: (mode: 'none' | 'heatmap' | 'terrain') => void;
  setTerrainResolution: (v: number) => void;
  setTerrainBands: (v: number) => void;
  
  // Layer toggle actions
  setShowScatter: (v: boolean) => void;
  setShowHulls: (v: boolean) => void;
  setShowVoronoi: (v: boolean) => void;
  
  lassoMode: boolean; // true when drawing polygon
  setLassoMode: (v: boolean) => void;
  
  selectedPolygon: [number, number][] | null;
  setSelectedPolygon: (poly: [number, number][] | null) => void;
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
  
  // Density overlay defaults
  heatmapVisible: true,
  heatmapOpacity: 35,
  selectedIds: [],
  
  clusterPolygons: {},
  
  // Overlay defaults
  overlayMode: 'heatmap' as 'heatmap',
  terrainResolution: 20,
  terrainBands: 6,
  
  // Layer toggles defaults
  showScatter: true,
  showHulls: true,
  showVoronoi: false,
  
  lassoMode: false, // true when drawing polygon
  selectedPolygon: null,
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
    
    // Extract per-cluster hulls if present
    const polygons: Record<number, [number, number][]> = {};
    // @ts-ignore – backend may include clusters field
    if (data?.clustering_info?.clusters) {
      // eslint-disable-next-line guard-for-in
      for (const cid in data.clustering_info.clusters) {
        const summary = (data.clustering_info.clusters as any)[cid];
        if (summary?.hull) polygons[Number(cid)] = summary.hull as [number, number][];
      }
    }

    set({ 
      projectionData: data, 
      clusterLabels: {}, // Reset labels on new data
      selectedCluster: null, // Reset selection on new data
      clusterPolygons: polygons,
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
  
  // ===== Density overlay & selection actions =====
  setHeatmap: (v) => {
    console.log('🌡️ Toggle heatmap overlay:', v);
    set({ heatmapVisible: v });
  },
  setHeatmapOpacity: (x) => {
    console.log('🌫️ Set heatmap opacity:', x);
    set({ heatmapOpacity: x });
  },
  setSelectedIds: (ids) => {
    console.log('✂️ Set selected IDs:', ids.length);
    set({ selectedIds: ids });
  },
  
  // ===== Overlay settings =====
  setOverlayMode: (mode) => set({ overlayMode: mode }),
  setTerrainResolution: (v) => set({ terrainResolution: v }),
  setTerrainBands: (v) => set({ terrainBands: v }),
  
  // ===== Layer toggles =====
  setShowScatter: (v) => {
    console.log('🟣 Toggle scatter layer:', v);
    set({ showScatter: v });
  },
  setShowHulls: (v) => {
    console.log('🔶 Toggle hull layer:', v);
    set({ showHulls: v });
  },
  setShowVoronoi: (v) => {
    console.log('📐 Toggle voronoi layer:', v);
    set({ showVoronoi: v });
  },
  
  resetState: () => {
    console.log('🔄 Resetting latent space state');
    set(initialState);
  },
  
  setLassoMode: (v) => {
    console.log('🟢 Toggle lasso mode:', v);
    set({ lassoMode: v });
  },
  
  setSelectedPolygon: (poly) => {
    console.log('✏️ Set selected polygon vertices:', poly?.length);
    set({ selectedPolygon: poly });
  },
})); 