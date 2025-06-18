# Sprint 11 Technical Implementation Plan

## Overview - POC COMPLETE ✅
This document outlines the technical implementation plan for Sprint 11 focusing on interactive latent space visualization with clustering capabilities. **Phase 1 POC is now complete and working.**

## Current Status - POC SUCCESS ✅

### ✅ COMPLETED Issues (POC Phase)
- **Network Connectivity**: Fixed API port mismatch (8000 vs 8002)
- **Import Errors**: Resolved qdrant_client import issues in backend
- **Hydration Errors**: Fixed React SSR mismatches in frontend
- **Navigation**: Added latent space access via dashboard card
- **DeckGL Integration**: Successfully implemented WebGL scatter plot rendering
- **Data Loading**: 25 points loading successfully from "wejele" collection
- **Viewport Calculation**: Auto-centering camera on data points
- **React Suspense**: Proper SSR handling for DeckGL components

### 🎯 NEXT PHASE Priorities (Interactivity & Clustering)

#### 1. Clustering Visualization (Immediate Priority)
**Current State**: Basic red dots rendering successfully
**Target State**: Color-coded clusters with outlier highlighting
- **Root Cause**: Clustering data available but not visualized
- **Impact**: Users can't distinguish between clusters
- **Solution**: Implement dynamic color palette based on cluster_id

#### 2. Interactive Features (Week 2 Priority)  
**Current State**: Basic zoom/pan working
**Target State**: Hover effects, click handlers, selection
- **Root Cause**: No point interaction handlers implemented
- **Impact**: Users can't explore individual points
- **Solution**: Add hover tooltips and click-through to image details

Current working API response:
```json
{
  "points": [
    {
      "id": "uuid",
      "x": 17.892,
      "y": 8.814,
      "cluster_id": 0,
      "is_outlier": false,
      "thumbnail_base64": "~4KB base64 string",
      "filename": "DSC07351.dng"
    }
  ],
  "collection": "wejele",
  "clustering_info": {
    "algorithm": "dbscan",
    "n_clusters": 3,
    "silhouette_score": 0.45,
    "n_outliers": 2
  }
}
```
- 25 points loading successfully
- Clustering data available but not visualized
- Performance acceptable for POC scale

## Next Phase Implementation Strategy

### Phase 2A: Clustering Visualization (Immediate - Week 2)

#### A. Dynamic Color Palette Implementation
```typescript
// Update UMAPScatterPlot.tsx - IMMEDIATE PRIORITY
const getClusterColor = (clusterId: number | undefined, isOutlier: boolean, totalClusters: number) => {
  if (isOutlier) return [255, 107, 107, 180]; // Red with transparency
  if (clusterId === undefined) return [150, 150, 150, 200]; // Grey
  
  // Use HSL color space for better distribution
  const hue = (clusterId / Math.max(1, totalClusters - 1)) * 360;
  const [r, g, b] = hslToRgb(hue / 360, 0.7, 0.6);
  return [r, g, b, 220];
};

// Enhanced ScatterplotLayer
const scatterplotLayer = new ScatterplotLayer({
  id: 'umap-points',
  data: points,
  getPosition: d => [d.x, d.y],
  getFillColor: d => getClusterColor(d.cluster_id, d.is_outlier, totalClusters),
  getRadius: 8,
  radiusMinPixels: 3,
  radiusMaxPixels: 15,
  pickable: true,
  autoHighlight: true,
});
```

#### B. Interactive Point Selection
```typescript
// Add hover and click handlers
const handlePointHover = (info: PickingInfo) => {
  if (info.object) {
    setHoveredPoint(info.object);
    // Show tooltip with image metadata
  } else {
    setHoveredPoint(null);
  }
};

const handlePointClick = (info: PickingInfo) => {
  if (info.object) {
    setSelectedPoint(info.object);
    // Open ImageDetailsModal or show detailed view
  }
};
```

### Phase 2B: Control Integration (Week 2)

#### A. Connect Clustering Controls
```typescript
// Wire ClusteringControls to useUMAP hook
const ClusteringControls = () => {
  const { clusteringMutation } = useUMAP();
  const { clusteringParams, updateClusteringParams } = useLatentSpaceStore();
  
  const handleParameterUpdate = (newParams: Partial<ClusteringRequest>) => {
    updateClusteringParams(newParams);
    // Debounced update to avoid excessive API calls
    debouncedClusteringUpdate({ ...clusteringParams, ...newParams });
  };
  
  const debouncedClusteringUpdate = useMemo(
    () => debounce((params: ClusteringRequest) => {
      clusteringMutation.mutate(params);
    }, 1000),
    [clusteringMutation]
  );
};
```

#### B. Real-time Metrics Display
```typescript
// Connect MetricsPanel to clustering data
const MetricsPanel = () => {
  const { projectionData } = useLatentSpaceStore();
  const clusteringInfo = projectionData?.clustering_info;
  
  if (!clusteringInfo) return null;
  
  return (
    <Card>
      <CardBody>
        <SimpleGrid columns={2} spacing={4}>
          <Stat>
            <StatLabel>Clusters</StatLabel>
            <StatNumber>{clusteringInfo.n_clusters}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Outliers</StatLabel>
            <StatNumber>{clusteringInfo.n_outliers}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Quality Score</StatLabel>
            <StatNumber>{clusteringInfo.silhouette_score?.toFixed(3)}</StatNumber>
          </Stat>
        </SimpleGrid>
      </CardBody>
    </Card>
  );
};
```

### Phase 2C: Advanced Features (Week 3)

#### A. Thumbnail Overlay System
```typescript
// Implement hover-based thumbnails
const ThumbnailOverlay = ({ hoveredPoint }: { hoveredPoint: UMAPPoint | null }) => {
  if (!hoveredPoint?.thumbnail_base64) return null;
  
  return (
    <Portal>
      <Box
        position="fixed"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        bg="white"
        p={4}
        borderRadius="md"
        boxShadow="lg"
        zIndex={1000}
      >
        <Image
          src={`data:image/jpeg;base64,${hoveredPoint.thumbnail_base64}`}
          alt={hoveredPoint.filename}
          maxW="200px"
          maxH="200px"
        />
        <Text mt={2} fontSize="sm">{hoveredPoint.filename}</Text>
      </Box>
    </Portal>
  );
};
```

## Updated Implementation Timeline

### ✅ Week 1: POC Complete
- [x] Backend validation and API integration
- [x] Basic DeckGL scatter plot rendering
- [x] Data loading and viewport calculation
- [x] React Suspense and SSR compatibility

### 🔄 Week 2: Interactivity & Clustering (CURRENT PRIORITY)
- [ ] **Day 1-2**: Implement clustering color visualization
- [ ] **Day 3-4**: Add hover and click interactions
- [ ] **Day 5**: Connect clustering controls to live updates

### ⏳ Week 3: Advanced Features
- [ ] **Day 1-2**: Thumbnail overlay system
- [ ] **Day 3-4**: Cluster labeling interface
- [ ] **Day 5**: Performance optimization for larger datasets

### 🎯 Week 4: Polish & Performance
- [ ] **Day 1-2**: Accessibility improvements and responsive design
- [ ] **Day 3-4**: Performance benchmarking and optimization
- [ ] **Day 5**: Final testing and documentation

## Success Metrics - Updated

### ✅ POC Success Metrics (Achieved)
- **Basic Rendering**: 25 points displaying successfully
- **Data Integration**: API calls working correctly
- **Viewport Management**: Auto-centering functional
- **Framework Integration**: DeckGL + React working smoothly

### 🎯 Next Phase Targets
- **Clustering Visualization**: Color-coded clusters visible
- **Interaction Response**: <100ms hover/click response
- **Control Integration**: Real-time parameter updates
- **Thumbnail Loading**: <500ms preview display

### 🚀 Final Sprint Targets
- **Performance**: <3s load for 1000+ points
- **Accessibility**: >90% audit score
- **User Experience**: Smooth exploration workflow
- **Feature Completeness**: All clustering algorithms functional

## Technical Architecture - Updated

### ✅ Proven Architecture (POC)
- **Frontend**: Next.js 15 + DeckGL + Chakra UI
- **State Management**: Zustand store with React Query
- **Rendering**: WebGL-accelerated scatter plots
- **Backend**: FastAPI with enhanced UMAP endpoints

### 🔄 Architecture Enhancements (Next Phase)
- **Color Management**: HSL-based dynamic palettes
- **Interaction Layer**: Hover/click event handling
- **Performance**: Viewport-based optimization
- **Accessibility**: ARIA labels and keyboard navigation

---

**Immediate Next Actions (Week 2):**
1. **Implement clustering colors** - Update getFillColor logic in UMAPScatterPlot
2. **Add interaction handlers** - Hover tooltips and click selection
3. **Connect clustering controls** - Wire UI controls to backend updates
4. **Performance monitoring** - Track interaction latency and render times

## Overview

This document provides the detailed technical implementation roadmap for the **Latent Space Visualization Tab** feature, building on the enhanced UMAP backend capabilities and following established frontend patterns.

## Phase 1: Foundation & Setup (Week 1)

### 1.1 Backend Validation & Testing

**Objective:** Verify the enhanced UMAP clustering endpoints work as expected. (Status: ✅ Verified)

**Tasks:**
- [x] **Test Basic UMAP Projection Endpoint**
- [x] **Test Enhanced Clustering Endpoint** 
- [x] **Performance Benchmark Testing** - *Initial tests confirm viability. Deeper benchmarks moved to Phase 4.*

**Expected Deliverables:**
- [x] Backend validation report with performance metrics.
- [x] Documented API examples for frontend integration.

### 1.2 Frontend Project Structure Setup

**Objective:** Create the foundational project structure. (Status: ✅ Verified)

**File Structure to Create/Verify:**
```
frontend/src/app/latent-space/
├── page.tsx                    # Main latent space page (Exists)
├── components/
│   ├── UMAPScatterPlot.tsx     # Core visualization component (To be created)
│   ├── ClusteringControls.tsx  # Parameter controls (To be created)
│   ├── MetricsPanel.tsx        # Quality metrics display (To be created)
│   ├── ThumbnailOverlay.tsx    # Image preview overlay (To be created)
│   └── ClusterLabelingPanel.tsx # NEW: Component for naming clusters
├── hooks/
│   ├── useUMAP.ts              # UMAP data fetching (To be created)
│   └── useLatentSpaceStore.ts  # Zustand store slice (To be created)
└── types/
    └── latent-space.ts         # TypeScript definitions (To be created)
```

**Implementation Steps:**

1.  **Create Main Page Route** - (✅ Done)
2.  **Define TypeScript Interfaces**
   ```typescript
   // frontend/src/app/latent-space/types/latent-space.ts
   export interface UMAPPoint {
     id: string;
     x: number;
     y: number;
     cluster_id?: number;
     is_outlier: boolean;
     thumbnail_base64?: string;
     filename?: string;
     caption?: string;
   }
   
   export interface ClusterInfo {
     id: number;
     label?: string; // User-defined label
     point_count: number;
   }

   export interface ClusteringInfo {
     algorithm: string;
     n_clusters: number;
     silhouette_score?: number;
     n_outliers?: number;
     parameters: Record<string, any>;
   }
   
   export interface UMAPProjectionResponse {
     points: UMAPPoint[];
     collection: string;
     clustering_info?: ClusteringInfo;
   }
   
   export interface ClusteringRequest {
     algorithm: 'dbscan' | 'kmeans' | 'hierarchical';
     n_clusters?: number;
     eps?: number;
     min_samples?: number;
   }
   
   export interface ViewportTransform {
     x: number;
     y: number;
     scale: number;
   }

   export interface ClusterLabelRequest {
     cluster_id: number;
     label: string;
   }
   ```

3.  **Set up Zustand Store Slice**
   ```typescript
   // frontend/src/app/latent-space/hooks/useLatentSpaceStore.ts
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
   ```

### 1.3 Navigation Integration

**Objective:** Add "Latent Space" link to existing sidebar navigation. (Status: ✅ Verified)

**Implementation:**
- [x] **Update Sidebar Component** - Link already exists in `frontend/src/components/Sidebar.tsx`.

**Expected Deliverables:**
- [x] Updated sidebar navigation with "Latent Space" link.
- [x] Basic page route accessible and rendering.
- [ ] TypeScript interfaces defined for all data structures.
- [ ] Zustand store slice configured and integrated.

## Phase 2: Core Visualization Implementation (Week 2)

### 2.1 High-Performance Rendering with Deck.gl

**Objective:** Set up Deck.gl for "snappy fast" scatter plot rendering, replacing the initial D3.js plan.

**Rationale:** To meet the performance requirements for large datasets and achieve advanced visual effects, we will use Deck.gl, which leverages WebGL for hardware-accelerated rendering.

**Installation:**
```bash
npm install deck.gl @deck.gl/react @deck.gl/layers luma.gl
```

**Base Component Structure:**
```typescript
// frontend/src/app/latent-space/components/UMAPScatterPlot.tsx
'use client';

import React, { useMemo } from 'react';
import { Box, Spinner, Center } from '@chakra-ui/react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';
import { scaleLinear } from 'd3-scale'; // Using d3-scale for color interpolation

interface UMAPScatterPlotProps {
  data: UMAPProjectionResponse | null;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
}

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 0,
  zoom: 1,
  pitch: 0,
  bearing: 0,
};

// Define the purple-to-yellow color scale
const purpleYellow = scaleLinear<string>()
  .domain([0, 1])
  .range(['#5B2C6F', '#F1C40F']);


export function UMAPScatterPlot({
  data,
  onPointHover,
  onPointClick,
  selectedClusterId,
}: UMAPScatterPlotProps) {

  const layers = useMemo(() => {
    if (!data?.points) return [];

    const nClusters = data.clustering_info?.n_clusters ?? 1;
    const colorScale = (clusterId: number) => purpleYellow(clusterId / Math.max(1, nClusters -1));

    return [
      new ScatterplotLayer<UMAPPoint>({
        id: 'scatterplot-layer',
        data: data.points,
        getPosition: d => [d.x, d.y, 0],
        getFillColor: d => {
          if (d.is_outlier) return [128, 128, 128, 150]; // Grey for outliers
          if (d.cluster_id === undefined) return [150, 150, 150, 200];
          
          const color = colorScale(d.cluster_id);
          const rgb = color.substring(4, color.length-1).replace(/ /g, '').split(',').map(Number);
          
          // Dim non-selected clusters
          if (selectedClusterId !== null && d.cluster_id !== selectedClusterId) {
            return [...rgb, 50];
          }

          return [...rgb, 220];
        },
        getRadius: 8, // Adjust for visual preference
        pointRadiusMinPixels: 2,
        pointRadiusMaxPixels: 15,
        pickable: true,
        onHover: info => onPointHover?.(info.object as UMAPPoint),
        onClick: info => onPointClick?.(info.object as UMAPPoint),
        
        // Performance and aesthetics from research
        parameters: {
          blend: true,
          // Additive blending for highlighting dense areas
          blendEquation: 'FUNC_ADD',
          blendFunc: ['SRC_ALPHA', 'ONE', 'ONE', 'ONE_MINUS_SRC_ALPHA'],
        }
      }),
    ];
  }, [data, onPointHover, onPointClick, selectedClusterId]);

  if (!data) {
    return (
      <Center h={600} bg="gray.50" borderRadius="md">
        <Spinner size="xl" />
      </Center>
    );
  }
  
  return (
    <Box position="relative" h="70vh" bg="transparent" borderRadius="md">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      >
      </DeckGL>
    </Box>
  );
}
```

### 2.2 UMAP Data Fetching Hook

**Objective:** Create custom hook for fetching and managing UMAP data, including cluster labeling.

```typescript
// frontend/src/app/latent-space/hooks/useUMAP.ts
// ... existing code ...
import { api } from '@/lib/api';
import { UMAPProjectionResponse, ClusteringRequest, ClusterLabelRequest } from '../types/latent-space';
import { useStore } from '@/store/useStore';

const fetchUMAPProjection = async (
// ... existing code ...
  const response = await api.get(`/umap/projection`, {
    params: { sample_size: sampleSize }
  });
  return response.data;
};

const fetchUMAPWithClustering = async (
// ... existing code ...
  const response = await api.post(`/umap/projection_with_clustering`, clusteringRequest, {
    params: { sample_size: sampleSize }
  });
  return response.data;
};

const postClusterLabel = async (
  collection: string,
  labelRequest: ClusterLabelRequest
): Promise<void> => {
  await api.post(`/umap/cluster_label`, labelRequest, {
    params: { collection_name: collection }
  });
};

export function useUMAP(sampleSize: number = 500) {
  const { collection } = useStore();
// ... existing code ...
    queryKey: ['umap', 'projection', collection, sampleSize],
    queryFn: () => fetchUMAPProjection(collection, sampleSize),
    enabled: !!collection,
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
```

### 2.3 Backend Endpoint for Cluster Labeling

**Objective:** Create a new backend endpoint to persist user-defined cluster labels.

**Implementation (in `backend/ingestion_orchestration_fastapi_app/routers/umap.py`):**
```python
# Add to imports
from qdrant_client.http.models import UpdateStatus, PointOps, Filter, FieldCondition, MatchValue

# ... existing code ...

class ClusterLabelRequest(BaseModel):
    cluster_id: int
    label: str

# ... existing code ...
def _find_optimal_k(data: np.ndarray, max_k: int = 10) -> int:
    """Find optimal number of clusters using silhouette analysis."""
    # ... implementation from previous context ...
    return best_k

@router.post("/cluster_label", status_code=204, summary="Assign a label to a cluster")
async def label_cluster(
    label_request: ClusterLabelRequest,
    collection_name: str = Depends(get_active_collection),
    qdrant: QdrantClient = Depends(get_qdrant_client),
):
    """Assign a persistent 'cluster_label' to all points in a given cluster."""
    try:
        qdrant.set_payload(
            collection_name=collection_name,
            payload={"user_cluster_label": label_request.label},
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="cluster_id", # Assumes cluster_id is stored in payload
                        match=MatchValue(value=label_request.cluster_id)
                    )
                ]
            ),
            wait=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to label cluster: {e}")
    return

@router.get("/cluster_analysis/{cluster_id}")
async def get_cluster_analysis(
    # ... implementation from previous context ...
```
**Note:** This requires that `cluster_id` is persisted to the point's payload after the clustering run. This implies a change in the `umap_projection_with_clustering` endpoint to store results.

**Expected Deliverables:**
- Functional UMAPScatterPlot component using Deck.gl
- High-performance zoom/pan and interactive points
- Correct color-coding for clusters and outliers as per design
- API integration hook for data fetching and labeling
- New backend endpoint for persisting cluster labels

## Phase 3: Advanced Features & Controls (Week 3)

### 3.1 Auto-Cataloging Interface (Cluster Labeling)

**Objective:** Build an interface for users to name discovered clusters, fulfilling the "auto-cataloging" requirement.

```typescript
// frontend/src/app/latent-space/components/ClusterLabelingPanel.tsx
'use client';

import React, { useState } from 'react';
import {
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  useToast,
  Box,
  Badge,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { useUMAP } from '../hooks/useUMAP';
import { ClusterLabelRequest } from '../types/latent-space';

export function ClusterLabelingPanel() {
  const { projectionData, setClusterLabel, clusterLabels } = useLatentSpaceStore();
  const { labelMutation } = useUMAP();
  const toast = useToast();
  const [localLabels, setLocalLabels] = useState<Record<number, string>>({});

  const handleLabelChange = (clusterId: number, label: string) => {
    setLocalLabels(prev => ({ ...prev, [clusterId]: label }));
  };

  const handleSaveLabel = (clusterId: number) => {
    const label = localLabels[clusterId];
    if (!label) return;

    const request: ClusterLabelRequest = { cluster_id: clusterId, label };
    labelMutation.mutate(request, {
      onSuccess: () => {
        setClusterLabel(clusterId, label); // Update global store
        toast({
          title: `Cluster ${clusterId} labeled as "${label}"`,
          status: 'success',
          duration: 2000,
        });
      },
      onError: (error) => {
        toast({
          title: 'Failed to save label',
          description: error.message,
          status: 'error',
        });
      },
    });
  };

  if (!projectionData?.clustering_info?.n_clusters) {
    return null;
  }
  
  const clusterIds = [...new Set(projectionData.points.map(p => p.cluster_id).filter(id => id !== undefined && id !== null))]
    .sort((a, b) => a - b);

  return (
    <Card>
      <CardHeader><Heading size="md">Auto-Catalog Clusters</Heading></CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          {clusterIds.map(id => (
            <HStack key={id} spacing={3}>
              <Badge colorScheme="purple" p={2} borderRadius="md">Cluster {id}</Badge>
              <Input
                placeholder={`Name for Cluster ${id}`}
                value={localLabels[id] || clusterLabels[id] || ''}
                onChange={(e) => handleLabelChange(id, e.target.value)}
              />
              <Button
                size="sm"
                onClick={() => handleSaveLabel(id)}
                isLoading={labelMutation.isPending && labelMutation.variables?.cluster_id === id}
              >
                Save
              </Button>
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
}
```

### 3.2 Clustering Controls Interface

**Objective:** Build parameter adjustment interface for clustering algorithms

```typescript
// frontend/src/app/latent-space/components/ClusteringControls.tsx
'use client';

// ... (Implementation mostly unchanged from original plan, just ensure it works with the new hooks)
// ... existing code ...
```

### 3.3 Metrics Panel Component

**Objective:** Display clustering quality metrics and performance data

```typescript
// frontend/src/app/latent-space/components/MetricsPanel.tsx
'use client';
// ... (Implementation mostly unchanged from original plan)
// ... existing code ...
```

### 3.4 Thumbnail Overlay System

**Objective:** Implement image preview overlays for scatter plot interactions

```typescript
// frontend/src/app/latent-space/components/ThumbnailOverlay.tsx
'use client';
// ... (Implementation mostly unchanged from original plan)
// ... existing code ...
```

**Expected Deliverables:**
- Complete ClusterLabelingPanel component for naming clusters
- Complete ClusteringControls component with real-time parameter adjustment
- MetricsPanel component displaying clustering quality metrics
- ThumbnailOverlay component for interactive image previews
- Debounced parameter updates to avoid excessive API calls
- Integration with existing ImageDetailsModal for detailed view

2. **Add Required Icon Import**
   ```typescript
   import { FiPlus, FiTrash2, FiRefreshCw, FiGrid, FiHome, FiScatter } from 'react-icons/fi';
   ```

**Core Rendering Logic:**
```
// ... (Implementation mostly unchanged from original plan)
// ... existing code ...

  const renderAlgorithmSpecificControls = () => {
    switch (clusteringParams.algorithm) {
      case 'dbscan':
        return (
          <>
            <FormControl>
              <FormLabel>Eps (neighborhood distance)</FormLabel>
              <NumberInput
                value={clusteringParams.eps}
                min={0.1}
                max={2.0}
                step={0.1}
                onChange={(_, value) => handleParameterChange({ eps: value })}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel>Min Samples</FormLabel>
              <NumberInput
                value={clusteringParams.min_samples}
                min={1}
                max={20}
                onChange={(_, value) => handleParameterChange({ min_samples: value })}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
          </>
        );
      case 'kmeans':
      case 'hierarchical':
        return (
          <FormControl>
            <FormLabel>Number of Clusters</FormLabel>
            <NumberInput
              value={clusteringParams.n_clusters || 5}
              min={2}
              max={20}
              onChange={(_, value) => handleParameterChange({ n_clusters: value })}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        );
      default:
        return null;
    }
  };

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Clustering Controls</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          <FormControl>
            <FormLabel>Algorithm</FormLabel>
            <Select
              value={clusteringParams.algorithm}
              onChange={(e) =>
                handleParameterChange({ 
                  algorithm: e.target.value as ClusteringRequest['algorithm'] 
                })
              }
            >
              <option value="dbscan">DBSCAN</option>
              <option value="kmeans">K-Means</option>
              <option value="hierarchical">Hierarchical</option>
            </Select>
          </FormControl>

          <Divider />

          {renderAlgorithmSpecificControls()}

          <Button
            isLoading={clusteringMutation.isPending}
            loadingText="Updating..."
            onClick={() => debouncedParameterUpdate(clusteringParams)}
            colorScheme="blue"
          >
            Apply Clustering
          </Button>
        </VStack>
      </CardBody>
    </Card>
  );
}

  return (
    <Card bg={cardBg}>
      <CardHeader>
        <HStack justify="space-between" align="center">
          <Heading size="md">Clustering Metrics</Heading>
          <Badge colorScheme="blue" variant="subtle">
            {clusteringInfo.algorithm}
          </Badge>
        </HStack>
      </CardHeader>
      <CardBody>
        <VStack spacing={6} align="stretch">
          {/* Cluster Overview */}
          <SimpleGrid columns={2} spacing={4}>
            <Stat bg={statBg} p={3} borderRadius="md">
              <StatLabel>Total Clusters</StatLabel>
              <StatNumber>{clusteringInfo.n_clusters}</StatNumber>
            </Stat>
            <Stat bg={statBg} p={3} borderRadius="md">
              <StatLabel>Outliers</StatLabel>
              <StatNumber>{clusteringInfo.n_outliers || 0}</StatNumber>
              <StatHelpText>
                {((clusteringInfo.n_outliers || 0) / totalPoints * 100).toFixed(1)}%
              </StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* Quality Metrics */}
          {clusteringInfo.silhouette_score && (
            <>
              <Divider />
              <VStack spacing={3} align="stretch">
                <Text fontWeight="semibold">Clustering Quality</Text>
                <HStack justify="space-between">
                  <Text fontSize="sm">Silhouette Score</Text>
                  <Badge colorScheme={getQualityColor(clusteringInfo.silhouette_score)}>
                    {getQualityLabel(clusteringInfo.silhouette_score)}
                  </Badge>
                </HStack>
                <Progress
                  value={clusteringInfo.silhouette_score * 100}
                  colorScheme={getQualityColor(clusteringInfo.silhouette_score)}
                  size="lg"
                />
                <Text fontSize="sm" color="gray.600">
                  Score: {clusteringInfo.silhouette_score.toFixed(3)}
                </Text>
              </VStack>
            </>
          )}

          {/* Algorithm Parameters */}
          <Divider />
          <VStack spacing={2} align="stretch">
            <Text fontWeight="semibold">Parameters</Text>
            {Object.entries(clusteringInfo.parameters).map(([key, value]) => (
              <HStack key={key} justify="space-between">
                <Text fontSize="sm" color="gray.600">{key}:</Text>
                <Text fontSize="sm">{value}</Text>
              </HStack>
            ))}
          </VStack>

          {/* Performance */}
          {loadingTime && (
            <>
              <Divider />
              <Stat bg={statBg} p={3} borderRadius="md">
                <StatLabel>Processing Time</StatLabel>
                <StatNumber>{loadingTime.toFixed(0)}ms</StatNumber>
                <StatHelpText>
                  {totalPoints} points processed
                </StatHelpText>
              </Stat>
            </>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}