'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { Box, Spinner, Center, Text, VStack, Alert, AlertIcon, Badge, HStack, Divider, Button } from '@chakra-ui/react';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';
import { 
  getEnhancedClusterColor, 
  getClusterColor,
  calculateBounds,
  ColorPaletteName,
  calculateClusterStatistics,
  getAnimatedClusterColor,
  getClusterSummary,
  getComplement
} from '../utils/visualization';
import { COORDINATE_SYSTEM, OrthographicView } from '@deck.gl/core';
import { luma } from '@luma.gl/core';
import { webgl2Adapter } from '@luma.gl/webgl';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { interpolateRgb } from 'd3-interpolate';
import { Delaunay } from 'd3-delaunay';
import { api, selectCollection as selectCollectionApi } from '@/lib/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useStore } from '@/store/useStore';
// Dynamic drawing layer
import booleanPointInPolygon from '@turf/boolean-point-in-polygon';
import { point as turfPoint } from '@turf/helpers';

// Lazy load DeckGL to avoid SSR issues
const DeckGL = React.lazy(() => import('@deck.gl/react'));

interface UMAPScatterPlotProps {
  data: UMAPProjectionResponse | null;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
  colorPalette?: ColorPaletteName;
  showOutliers?: boolean;
  pointSize?: number;
}

// Note: Utility functions moved to utils/visualization.ts

// Register the WebGL-2 adapter once. luma.registerAdapters() is idempotent,
// so calling it multiple times (e.g. during hot-reload) is safe.
try {
  luma.registerAdapters?.([webgl2Adapter]);
} catch (err) {
  /* eslint-disable no-console */
  console.warn('[UMAPScatterPlot] WebGL2 adapter registration failed', err);
}

export function UMAPScatterPlot({
  data,
  onPointHover,
  onPointClick,
  selectedClusterId,
  colorPalette = 'observable',
  showOutliers = true,
  pointSize = 10,
}: UMAPScatterPlotProps) {
  const [hoveredPoint, setHoveredPoint] = useState<UMAPPoint | null>(null);
  const [animationProgress, setAnimationProgress] = useState(0);
  const lassoMode = useLatentSpaceStore((s) => s.lassoMode);
  const setLassoMode = useLatentSpaceStore((s) => s.setLassoMode);
  const setSelectedIds = useLatentSpaceStore((s) => s.setSelectedIds);
  const setSelectedPolygon = useLatentSpaceStore((s) => s.setSelectedPolygon);
  const selectedIds = useLatentSpaceStore((s) => s.selectedIds);
  const projectionData = useLatentSpaceStore((s) => s.projectionData);
  const [screenPoly, _setScreenPoly] = useState<[number, number][]>([]);
  const screenPolyRef = React.useRef<[number, number][]>([]);
  const setScreenPoly = (value: [number, number][] | ((prev: [number, number][]) => [number, number][])) => {
    _setScreenPoly((prev) => {
      const newVal = typeof value === 'function' ? (value as any)(prev) : value;
      screenPolyRef.current = newVal;
      return newVal;
    });
  };
  const deckRef = React.useRef<any>(null);
  const overlayRef = React.useRef<HTMLDivElement>(null);

  // Animation loop for smooth transitions
  useEffect(() => {
    let animationId: number;
    let startTime: number;
    
    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const elapsed = currentTime - startTime;
      const progress = Math.sin(elapsed * 0.003) * 0.5 + 0.5; // Smooth sine wave
      setAnimationProgress(progress);
      animationId = requestAnimationFrame(animate);
    };
    
    if (selectedClusterId !== null || hoveredPoint) {
      animationId = requestAnimationFrame(animate);
    }
    
    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [selectedClusterId, hoveredPoint]);

  // Debug logging
  useEffect(() => {
    console.log('🎨 UMAPScatterPlot render:', {
      hasData: !!data,
      pointsCount: data?.points?.length,
      selectedClusterId,
      colorPalette,
      firstPoint: data?.points?.[0],
      samplePoints: data?.points?.slice(0, 3),
      clusteringInfo: data?.clustering_info,
    });
  }, [data, selectedClusterId, colorPalette]);

  // === Keyboard shortcuts ===
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'l' || e.key === 'L') setLassoMode(!lassoMode);
      if (e.key === 'Escape') {
        setLassoMode(false);
        setScreenPoly([]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lassoMode, setLassoMode]);

  // === Create collection mutation ===
  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: async (payload: { newName: string; ids: string[] }) => {
      const body = {
        new_collection_name: payload.newName,
        source_collection: data.collection,
        point_ids: payload.ids,
      };
      const res = await api.post('/api/v1/collections/from_selection', body);
      return res.data;
    },
    onSuccess: async (data, variables) => {
      setSelectedIds([]);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      // Automatically set new collection active both locally and on server
      const newCol = variables.newName;
      try {
        await selectCollectionApi(newCol);
      } catch (e) {
        // non-fatal
        console.warn('Failed to set active collection', e);
      }
      // optimistic local update
      const setCollection = useStore.getState().setCollection;
      setCollection(newCol);
      setShowModal(false);
    },
  });

  const [newName, setNewName] = useState('');
  const [showModal, setShowModal] = useState(false);

  // GeoJSON for drawing
  const [lassoGeoJson, setLassoGeoJson] = React.useState<any>({ type: 'FeatureCollection', features: [] });

  if (!data) {
    return (
      <Center h={600} bg="gray.50" borderRadius="md">
        <VStack>
          <Spinner size="xl" />
          <Text>Loading visualization...</Text>
        </VStack>
      </Center>
    );
  }

  if (!data.points || data.points.length === 0) {
    return (
      <Center h={600} bg="gray.50" borderRadius="md">
        <VStack>
          <Text fontSize="lg" color="gray.600">No points to visualize</Text>
          <Text fontSize="sm" color="gray.500">Add images to your collection to see them here</Text>
        </VStack>
      </Center>
    );
  }

  console.log('🎯 Rendering visualization with', data.points.length, 'points');
  
  return (
    <Box w="100%" position="relative" h="600px" bg="white" borderRadius="md" border="1px solid" borderColor="gray.200" overflow="hidden">
      <React.Suspense 
        fallback={
          <Center h="600px">
            <VStack>
              <Spinner size="xl" />
              <Text>Loading DeckGL...</Text>
            </VStack>
          </Center>
        }
      >
                    <EnhancedDeckGLVisualization deckRef={deckRef} lassoGeoJson={lassoGeoJson} setLassoGeoJson={setLassoGeoJson}
              points={data.points} 
              onPointHover={(point) => {
            setHoveredPoint(point);
            onPointHover?.(point);
          }}
          onPointClick={onPointClick}
          selectedClusterId={selectedClusterId}
          colorPalette={colorPalette}
          showOutliers={showOutliers}
          pointSize={pointSize}
        />
      </React.Suspense>
      
      {/* Enhanced info overlays */}
      <Box 
        position="absolute" 
        top={3} 
        left={3} 
        bg="blackAlpha.800" 
        color="white" 
        px={3} 
        py={2} 
        borderRadius="md" 
        fontSize="sm"
        fontWeight="medium"
        backdropFilter="blur(4px)"
      >
        <Text>{data.points.length} points</Text>
        <Text fontSize="xs" opacity={0.8}>
          {data.clustering_info?.n_clusters || 0} clusters • {colorPalette} palette
        </Text>
      </Box>
      
      {/* Enhanced hover tooltip with cluster summary */}
      {hoveredPoint && (
        <Box 
          position="absolute" 
          top={3} 
          right={3} 
          bg="blackAlpha.900" 
          color="white" 
          px={4} 
          py={3} 
          borderRadius="lg" 
          fontSize="sm" 
          maxW="320px"
          backdropFilter="blur(8px)"
          boxShadow="2xl"
          border="1px solid"
          borderColor="whiteAlpha.200"
        >
          <VStack align="start" spacing={2}>
            <HStack justify="space-between" w="full">
              <Text fontWeight="bold" fontSize="md" isTruncated maxW="200px">
                {hoveredPoint.filename || `Point ${hoveredPoint.id.slice(0, 8)}`}
              </Text>
              {(hoveredPoint.cluster_id !== null && hoveredPoint.cluster_id !== undefined) ? (
                <Badge colorScheme="purple" variant="solid" fontSize="xs">
                  Cluster {hoveredPoint.cluster_id}
                </Badge>
              ) : (
                <Badge colorScheme="gray" variant="solid" fontSize="xs">
                  Unclustered
                </Badge>
              )}
            </HStack>
            
            <Divider opacity={0.3} />
            
            <VStack align="start" spacing={1} fontSize="xs">
              <HStack>
                <Text color="gray.300">Position:</Text>
                <Text>({hoveredPoint.x.toFixed(2)}, {hoveredPoint.y.toFixed(2)})</Text>
              </HStack>
              
              {(hoveredPoint.cluster_id !== null && hoveredPoint.cluster_id !== undefined && data?.points) ? (
                (() => {
                  const summary = getClusterSummary(data.points, hoveredPoint.cluster_id!);
                  return (
                    <>
                      <HStack>
                        <Text color="gray.300">Cluster size:</Text>
                        <Text>{summary.size} points</Text>
                      </HStack>
                      <HStack>
                        <Text color="gray.300">Density:</Text>
                        <Text>{summary.density.toFixed(2)}</Text>
                      </HStack>
                    </>
                  );
                })()
              ) : (
                <HStack>
                  <Text color="gray.300">Status:</Text>
                  <Text>No clustering applied</Text>
                </HStack>
              )}
              
              {hoveredPoint.is_outlier && (
                <HStack>
                  <Text color="red.300" fontWeight="medium">🔍 Outlier</Text>
                </HStack>
              )}
            </VStack>
            
            {hoveredPoint.caption && (
              <>
                <Divider opacity={0.3} />
                <Text fontSize="xs" color="gray.200" lineHeight="1.4" isTruncated maxW="280px">
                  {hoveredPoint.caption}
                </Text>
              </>
            )}
          </VStack>
        </Box>
      )}

      {/* Cluster selection indicator */}
      {selectedClusterId !== null && selectedClusterId !== undefined && (
        <Box
          position="absolute"
          bottom={3}
          left={3}
          bg="purple.500"
          color="white"
          px={3}
          py={2}
          borderRadius="md"
          fontSize="sm"
          fontWeight="medium"
        >
          Selected: Cluster {selectedClusterId}
        </Box>
      )}

      {/* Create collection bar */}
      {selectedIds.length > 0 && (
        <Box position="fixed" bottom={6} left="50%" transform="translateX(-50%)" zIndex={3000} bg="white" _dark={{bg:'gray.800'}} px={4} py={2} borderRadius="md" boxShadow="xl" border="1px solid" borderColor="gray.300" _dark={{borderColor:'gray.600'}}>
          <HStack spacing={3}>
            <Text>{selectedIds.length} selected</Text>
            <Button size="sm" colorScheme="green" onClick={() => setShowModal(true)}>
              Create Collection
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>Clear</Button>
          </HStack>
        </Box>
      )}

      {/* Modal */}
      {showModal && (
        <Box position="fixed" inset={0} bg="blackAlpha.600" zIndex={1000} display="flex" alignItems="center" justifyContent="center">
          <Box bg="white" _dark={{bg:'gray.700'}} p={6} borderRadius="md" minW="300px">
            <VStack spacing={4}>
              <Text fontWeight="bold">New Collection Name</Text>
              <input style={{width:'100%', padding:'6px'}} value={newName} onChange={(e)=>setNewName(e.target.value)} />
              <HStack>
                <Button size="sm" colorScheme="green" isDisabled={!newName} isLoading={createMutation.isPending} onClick={() => createMutation.mutate({ newName, ids: selectedIds })}>Create</Button>
                <Button size="sm" onClick={()=> setShowModal(false)}>Cancel</Button>
              </HStack>
            </VStack>
          </Box>
        </Box>
      )}

      <Box
        position="absolute"
        inset={0}
        zIndex={2000}
        bg="transparent"
        pointerEvents="none"
        ref={overlayRef}
      >
        {screenPoly.length > 1 && (
          <svg style={{position:'absolute',inset:0,pointerEvents:'none'}}>
            <polyline points={screenPoly.map(p=>p.join(',')).join(' ')} fill="none" stroke="teal" strokeWidth="2" />
          </svg>
        )}
      </Box>
    </Box>
  );
}

function EnhancedDeckGLVisualization({ 
  deckRef,
  points, 
  onPointHover, 
  onPointClick, 
  selectedClusterId,
  colorPalette = 'observable',
  showOutliers = true,
  pointSize = 10,
  lassoGeoJson,
  setLassoGeoJson
}: {
  deckRef: React.RefObject<any>;
  points: UMAPPoint[];
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
  colorPalette?: ColorPaletteName;
  showOutliers?: boolean;
  pointSize?: number;
  lassoGeoJson: any;
  setLassoGeoJson: React.Dispatch<React.SetStateAction<any>>;
}) {
  const [DeckGLComponent, setDeckGLComponent] = React.useState<any>(null);
  const [ScatterplotLayerComponent, setScatterplotLayerComponent] = React.useState<any>(null);
  const [HeatmapLayerComponent, setHeatmapLayerComponent] = React.useState<any>(null);
  const [PolygonLayerComponent, setPolygonLayerComponent] = React.useState<any>(null);
  const [PathLayerComponent, setPathLayerComponent] = React.useState<any>(null);
  const [EditableGeoJsonLayerComponent, setEditableGeoJsonLayerComponent] = React.useState<any>(null);
  const [DrawPolygonByDraggingModeComponent, setDrawPolygonByDraggingModeComponent] = React.useState<any>(null);
  const [ViewModeComponent, setViewModeComponent] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [hoveredObject, setHoveredObject] = React.useState<UMAPPoint | null>(null);
  const selectedIds = useLatentSpaceStore((s) => s.selectedIds);
  const setSelectedIdsStore = useLatentSpaceStore((s) => s.setSelectedIds);

  // ===== Read needed store slices individually to avoid returning new objects each render =====
  const storeShowOutliers = useLatentSpaceStore((s) => s.showOutliers);
  const storePointSize = useLatentSpaceStore((s) => s.pointSize);
  const heatmapVisible = useLatentSpaceStore((s) => s.heatmapVisible);
  const heatmapOpacity = useLatentSpaceStore((s) => s.heatmapOpacity);
  const overlayMode = useLatentSpaceStore((s) => s.overlayMode);
  const terrainResolution = useLatentSpaceStore((s) => s.terrainResolution);
  const terrainBands = useLatentSpaceStore((s) => s.terrainBands);
  const clusterPolygons = useLatentSpaceStore((s) => s.clusterPolygons);
  const storeColorPalette = useLatentSpaceStore((s) => s.colorPalette);
  const showScatter = useLatentSpaceStore((s) => s.showScatter);
  const showHulls = useLatentSpaceStore((s) => s.showHulls);
  const showVoronoi = useLatentSpaceStore((s) => s.showVoronoi);
  const showVoronoiFill = useLatentSpaceStore((s)=>s.showVoronoiFill);
  const lassoMode = useLatentSpaceStore((s)=>s.lassoMode);
  const setLassoMode = useLatentSpaceStore((s)=>s.setLassoMode);
  const setSelectedPolygonStore = useLatentSpaceStore((s)=>s.setSelectedPolygon);

  // Resolve effective values: props override store when provided
  const effectiveShowOutliers = showOutliers !== undefined ? showOutliers : storeShowOutliers;
  const effectivePointSize = pointSize !== undefined ? pointSize : storePointSize;
  const effectiveColorPalette = colorPalette ?? storeColorPalette;

  useEffect(() => {
    const loadComponents = async () => {
      try {
        // ====== Runtime capability check ===================================
        // deck.gl v9 requires WebGL2. Abort early if the browser/GPU cannot
        // create a WebGL2 context so we can show a friendly message instead
        // of crashing deep inside luma.gl internal code.
        const testCanvas = document.createElement('canvas');
        const gl2 = testCanvas.getContext('webgl2');
        if (!gl2) {
          throw new Error(
            'WebGL2 is not supported in this browser / GPU. Enable hardware acceleration or use a more recent browser to view the 2-D embedding.'
          );
        }
        // ====================================================================

        console.log('📦 Loading DeckGL components...');
        
        const deckModule = await import('@deck.gl/react');
        const layersModule = await import('@deck.gl/layers');
        const aggModule = await import('@deck.gl/aggregation-layers');
        const editableModule = await import('@deck.gl-community/editable-layers');
        
        console.log('✅ DeckGL components loaded');
        setDeckGLComponent(() => deckModule.default);
        setScatterplotLayerComponent(() => layersModule.ScatterplotLayer);
        setHeatmapLayerComponent(() => aggModule.HeatmapLayer);
        setPolygonLayerComponent(() => layersModule.PolygonLayer);
        setPathLayerComponent(() => layersModule.PathLayer);
        setEditableGeoJsonLayerComponent(() => editableModule.EditableGeoJsonLayer);
        setDrawPolygonByDraggingModeComponent(() => editableModule.DrawPolygonByDraggingMode);
        setViewModeComponent(() => editableModule.ViewMode);
      } catch (err) {
        console.error('❌ Failed to load DeckGL:', err);
        setError(err instanceof Error ? err.message : 'Failed to load DeckGL');
      }
    };

    loadComponents();
  }, []);

  // WebGL Debug Test - moved to proper hooks order
  useEffect(() => {
    console.log('🧪 Testing WebGL support...');
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      
      if (gl) {
        console.log('✅ WebGL is supported in browser');
        console.log('🔍 WebGL info:', {
          version: gl.getParameter(gl.VERSION),
          vendor: gl.getParameter(gl.VENDOR),
          renderer: gl.getParameter(gl.RENDERER)
        });
      } else {
        console.log('❌ WebGL is not supported in browser');
      }
    } catch (error) {
      console.log('❌ WebGL test failed:', error);
    }
    
    // Check for existing canvases
    setTimeout(() => {
      const canvases = document.querySelectorAll('canvas');
      console.log(`🎨 Found ${canvases.length} canvas elements after render`);
      canvases.forEach((canvas, i) => {
        console.log(`Canvas ${i}:`, {
          width: canvas.width,
          height: canvas.height,
          context: canvas.getContext('webgl') ? 'WebGL' : 'Other'
        });
      });
    }, 1000);
  }, []);

  const orthoViewState = useMemo(() => {
    const bounds = calculateBounds(points, 0.15);
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    const maxDim = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY, 0.1);
    const zoom = Math.log2(600 / maxDim); // 600px canvas baseline
    return { target: [centerX, centerY, 0], zoom };
  }, [points]);

  // previous detailed logging kept but tied to ortho bounds
  useEffect(() => {
    const bounds = calculateBounds(points, 0.15);
    console.log('🗺️ Ortho bounds:', bounds);
    console.log('🗺️ Ortho viewState:', orthoViewState);
  }, [points, orthoViewState]);

  // Filter points based on showOutliers setting
  const filteredPoints = useMemo(() => {
    if (effectiveShowOutliers) return points;
    return points.filter(point => !point.is_outlier);
  }, [points, effectiveShowOutliers]);

  // Calculate cluster statistics for better color distribution
  const clusterStats = useMemo(() => {
    return calculateClusterStatistics(filteredPoints);
  }, [filteredPoints]);

  const layers = useMemo(() => {
    if (!ScatterplotLayerComponent) return [];

    const layerList: any[] = [];

    // === Heatmap layers (under scatter) ===
    if (overlayMode==='heatmap' && heatmapVisible && HeatmapLayerComponent) {
      // Group points by cluster id (exclude outliers/unclustered)
      const clustersMap: Record<number, UMAPPoint[]> = {};
      filteredPoints.forEach((p) => {
        if (p.cluster_id === undefined || p.cluster_id === null || p.cluster_id === -1) return;
        if (selectedClusterId !== null && selectedClusterId !== undefined && p.cluster_id !== selectedClusterId) return; // Respect selection filtering
        clustersMap[p.cluster_id] = clustersMap[p.cluster_id] || [];
        clustersMap[p.cluster_id].push(p);
      });

      Object.entries(clustersMap).forEach(([cidStr, pts]) => {
        const cid = Number(cidStr);
        const baseColor = getClusterColor({ cluster_id: cid, is_outlier: false } as any, clusterStats.totalClusters, effectiveColorPalette).slice(0,3) as [number,number,number];
        // HeatmapLayer expects colorRange[0] = HIGH intensity, [5] = LOW.
        // We want cluster centers (high weight) to be vivid, edges to fade to white.
        const colorRange = Array.from({ length: 6 }).map((_, idx) => {
          const t = idx / 5; // 0 → high, 1 → low
          const rgb = interpolateRgb(`rgb(${baseColor[0]},${baseColor[1]},${baseColor[2]})`, `#ffffff`)(t);
          const [r, g, b] = rgb.match(/\d+/g)!.map(Number);
          return [r, g, b, 255];
        });

        layerList.push(new HeatmapLayerComponent({
          id: `heatmap-${cid}`,
          data: pts,
          getPosition: (d: UMAPPoint) => [d.x, d.y],
          getWeight: 1,
          colorRange,
          radiusPixels: terrainResolution * 6,
          opacity: heatmapOpacity / 100,
          aggregation: 'MEAN',
          gpuAggregation: true,
        }));
      });
    }

    // ===== Polygon hull layers (under heatmap, under scatter) =====
    if (showHulls && PolygonLayerComponent && Object.keys(clusterPolygons).length) {
      Object.entries(clusterPolygons).forEach(([cidStr, hullCoords]) => {
        const cid = Number(cidStr);
        if (selectedClusterId !== null && selectedClusterId !== undefined && cid !== selectedClusterId) return;
        const baseColor = getClusterColor({ cluster_id: cid, is_outlier: false } as any, clusterStats.totalClusters, effectiveColorPalette);
        const fillCol = [...baseColor.slice(0,3), 140]; // stronger fill alpha

        layerList.push(new PolygonLayerComponent({
          id: `hull-${cid}`,
          data: [{ polygon: hullCoords }],
          getPolygon: (d:any)=>d.polygon,
          stroked: true,
          lineWidthUnits: 'pixels',
          lineWidthMinPixels: 1,
          filled: true,
          getFillColor: fillCol,
          getLineColor: baseColor,
          pickable: false,
          updateTriggers: { getFillColor: [effectiveColorPalette], getLineColor: [effectiveColorPalette] },
        }));
      });
    }

    // === Terrain overlay via blurred HeatmapLayer ===
    if (overlayMode === 'terrain' && HeatmapLayerComponent) {
      const clusterGroups: Record<number, UMAPPoint[]> = {};
      filteredPoints.forEach((p) => {
        if (p.cluster_id === undefined || p.cluster_id === null || p.cluster_id === -1) return;
        if (selectedClusterId !== null && selectedClusterId !== undefined && p.cluster_id !== selectedClusterId) return;
        clusterGroups[p.cluster_id] = clusterGroups[p.cluster_id] || [];
        clusterGroups[p.cluster_id].push(p);
      });

      Object.entries(clusterGroups).forEach(([cidStr, pts]) => {
        const cid = Number(cidStr);
        const baseColor = getClusterColor({ cluster_id: cid, is_outlier: false } as any, clusterStats.totalClusters, effectiveColorPalette).slice(0, 3);
        const colorRange = Array.from({ length: 6 }).map((_, idx) => {
          const t = idx / 5;
          return [
            baseColor[0] * (1 - t) + 255 * t,
            baseColor[1] * (1 - t) + 255 * t,
            baseColor[2] * (1 - t) + 255 * t,
            200,
          ];
        });

        layerList.push(
          new HeatmapLayerComponent({
            id: `terrain-heatmap-${cid}`,
            data: pts,
            getPosition: (d: UMAPPoint) => [d.x, d.y],
            getWeight: 1,
            colorRange,
            radiusPixels: terrainResolution * 3,
            opacity: heatmapOpacity / 100,
            gpuAggregation: true,
            aggregation: 'SUM',
            coordinateSystem: COORDINATE_SYSTEM.CARTESIAN,
          })
        );
      });
    }

    // === Voronoi boundaries ===
    if (showVoronoi && PathLayerComponent) {
      try {
        const bounds = calculateBounds(filteredPoints, 0.1);
        const delaunay = Delaunay.from(filteredPoints, (d)=>d.x, (d)=>d.y);
        const vor = delaunay.voronoi([bounds.minX, bounds.minY, bounds.maxX, bounds.maxY]);
        const paths: any[] = [];
        const cells: any[] = [];
        for (let i = 0; i < filteredPoints.length; i++) {
          const poly = vor.cellPolygon(i);
          if (!poly) continue;
          const pt = filteredPoints[i];
          const color = getClusterColor(pt, clusterStats.totalClusters, effectiveColorPalette);
          paths.push({
            path: poly.map(([x,y])=>[x,y]),
            cluster_id: pt.cluster_id,
            color,
          });

          if (showVoronoiFill) {
            const fillColor = getComplement(color, 80);
            cells.push({
              polygon: poly.map(([x,y])=>[x,y]),
              cluster_id: pt.cluster_id,
              fillColor,
            });
          }
        }

        layerList.push(new PathLayerComponent({
          id: 'voronoi-borders',
          data: paths,
          getPath: (d:any)=>d.path,
          getWidth: 2,
          widthUnits: 'pixels',
          getColor: (d:any)=>d.color,
          pickable: false,
        }));

        if (showVoronoiFill && cells.length && PolygonLayerComponent) {
          layerList.unshift(new PolygonLayerComponent({
            id: 'voronoi-tiles',
            data: cells,
            getPolygon: (d:any)=>d.polygon,
            getFillColor: (d:any)=>d.fillColor,
            getLineColor: [0,0,0,0],
            pickable: false,
            parameters: { depthTest: false },
            updateTriggers: { getFillColor: [effectiveColorPalette] },
          }));
        }
      } catch(err){
        console.warn('Voronoi computation failed', err);
      }
    }

    // === Lasso drawing ===
    if (
      EditableGeoJsonLayerComponent &&
      DrawPolygonByDraggingModeComponent &&
      ViewModeComponent
    ) {
      layerList.push(
        new EditableGeoJsonLayerComponent({
          id: 'lasso',
          data: lassoGeoJson,
          mode: lassoMode ? DrawPolygonByDraggingModeComponent : ViewModeComponent,
          pickable: lassoMode,
          parameters: { depthTest: false },
          getLineColor: [255, 255, 0],
          getLineWidth: 2,
          getCursor: () => (lassoMode ? 'crosshair' : 'auto'),
          selectedFeatureIndexes: [],
          onEdit: ({ updatedData, editType }) => {
            setLassoGeoJson(updatedData);
            if (editType !== 'addFeature') return;

            const polyFeature = updatedData.features.at(-1);
            if (!polyFeature) return;

            if (
              !polyFeature.geometry ||
              polyFeature.geometry.type !== 'Polygon' ||
              !Array.isArray((polyFeature.geometry as any).coordinates) ||
              !Array.isArray((polyFeature.geometry as any).coordinates[0]) ||
              (polyFeature.geometry as any).coordinates[0].length < 3
            ) {
              console.warn('🚫 Lasso polygon missing coordinates – selection skipped');
              return;
            }

            const idsSel: string[] = [];
            filteredPoints.forEach((pt) => {
              if (booleanPointInPolygon(turfPoint([pt.x, pt.y]), polyFeature.geometry as any)) {
                idsSel.push(pt.id);
              }
            });

            setSelectedIdsStore(idsSel);
            if (polyFeature.geometry?.type === 'Polygon' && Array.isArray(polyFeature.geometry.coordinates)) {
              // @ts-ignore – coordinates type
              setSelectedPolygonStore(polyFeature.geometry.coordinates[0]);
            }

            // Exit lasso mode but keep polygon rendered
            setLassoMode(false);
          },
          updateTriggers: {
            mode: [lassoMode],
            pickable: [lassoMode],
            data: [lassoGeoJson],
          },
        })
      );
    }

    const heatmapActive = overlayMode === 'heatmap' && heatmapVisible;

    // Scatter layer
    if (showScatter) {
      const enhancedScatterplotLayer = new ScatterplotLayerComponent({
        id: 'umap-points',
        data: filteredPoints,
        pickable: !lassoMode,
        stroked: true,
        lineWidthUnits: 'pixels',
        lineWidthMinPixels: 1,
        getLineColor: [0, 0, 0, 200],
        filled: true,
        radiusUnits: 'pixels',
        radiusMinPixels: effectivePointSize,
        getPosition: (d) => [d.x, d.y],
        getFillColor: (d) => {
          if (selectedIds && selectedIds.includes(d.id)) {
            // Highlight selected points with bright yellow
            return [255, 230, 0, 255];
          }
          const base = getEnhancedClusterColor(
            d,
            clusterStats.totalClusters,
            selectedClusterId ?? null,
            hoveredObject ? hoveredObject.id === d.id : false,
            effectiveColorPalette
          );
          // Reduce opacity when heatmap active so density shows through
          if (heatmapActive) {
            return [...base.slice(0, 3), 140];
          }
          return base;
        },
        getRadius: (d)=> selectedIds && selectedIds.includes(d.id) ? effectivePointSize*1.6 : effectivePointSize,
        updateTriggers: {
          getFillColor: [selectedIds, hoveredObject, selectedClusterId, effectiveColorPalette, heatmapActive],
          getRadius: [selectedIds, effectivePointSize],
          pickable: [lassoMode],
        },
        onHover: ({ object }) => {
          setHoveredObject(object as UMAPPoint | null);
          onPointHover?.(object as UMAPPoint | null);
        },
        onClick: ({ object }) => {
          if (object) onPointClick?.(object as UMAPPoint);
        },
        coordinateSystem: COORDINATE_SYSTEM.CARTESIAN,
      });

      layerList.push(enhancedScatterplotLayer);
    }

    return layerList;
  }, [
    ScatterplotLayerComponent,
    HeatmapLayerComponent,
    filteredPoints,
    selectedClusterId,
    hoveredObject,
    effectiveColorPalette,
    effectivePointSize,
    clusterStats.totalClusters,
    clusterStats.maxDim,
    heatmapVisible,
    heatmapOpacity,
    clusterPolygons,
    PolygonLayerComponent,
    overlayMode,
    terrainResolution,
    terrainBands,
    showScatter,
    showHulls,
    showVoronoi,
    showVoronoiFill,
    PathLayerComponent,
    selectedIds,
    lassoMode,
    points,
    EditableGeoJsonLayerComponent,
    DrawPolygonByDraggingModeComponent,
    ViewModeComponent,
    lassoGeoJson,
    setSelectedIdsStore,
    setSelectedPolygonStore,
  ]);

  if (error) {
    return (
      <Center h="600px">
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <VStack align="start">
            <Text fontWeight="semibold">Failed to load visualization</Text>
            <Text fontSize="sm">{error}</Text>
          </VStack>
        </Alert>
      </Center>
    );
  }

  if (!DeckGLComponent || !ScatterplotLayerComponent) {
    return (
      <Center h="600px">
        <VStack>
          <Spinner size="xl" color="purple.500" />
          <Text>Loading DeckGL components...</Text>
        </VStack>
      </Center>
    );
  }

  console.log('🎬 Rendering DeckGL with layers:', layers.length);
  
  return (
    <DeckGLComponent ref={deckRef}
      views={new OrthographicView({ id: 'ortho' })}
      initialViewState={orthoViewState}
      controller={{
        dragPan: true,
        dragRotate: false,
        scrollZoom: true,
        touchZoom: true,
        touchRotate: false,
        doubleClickZoom: true,
        keyboard: true,
      }}
      layers={layers}
      style={{ 
        width: '100%', 
        height: '100%',
        position: 'relative'
      }}
      getCursor={({ isDragging, isHovering }) => {
        if (lassoMode) return 'crosshair';
        if (isDragging) return 'grabbing';
        if (isHovering) return 'pointer';
        return 'grab';
      }}
      onViewStateChange={({ viewState }) => {
        console.log('🔄 Viewport changed:', viewState);
      }}
      onLoad={() => {
        console.log('✅ DeckGL loaded successfully - WebGL context ready');
      }}
      onError={(error) => {
        // deck.gl can sometimes forward non-Error objects – ensure we
        // always log something human readable to aid debugging.
        const details = error instanceof Error ? error.message : JSON.stringify(error ?? {});
        console.error('❌ DeckGL error:', details, error);
      }}
      deviceProps={{
        type: 'webgl',
        webgl: {
          antialias: false,
          powerPreference: 'high-performance',
          preserveDrawingBuffer: false
        }
      }}
    />
  );
} 