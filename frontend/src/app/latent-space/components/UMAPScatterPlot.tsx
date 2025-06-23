'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { Box, Spinner, Center, Text, VStack, Alert, AlertIcon, Badge, HStack, Divider } from '@chakra-ui/react';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';
import { 
  getEnhancedClusterColor, 
  getClusterColor,
  calculateBounds,
  ColorPaletteName,
  calculateClusterStatistics,
  getAnimatedClusterColor,
  getClusterSummary
} from '../utils/visualization';
import { COORDINATE_SYSTEM, OrthographicView } from '@deck.gl/core';
import { luma } from '@luma.gl/core';
import { webgl2Adapter } from '@luma.gl/webgl';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { interpolateRgb } from 'd3-interpolate';

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
                    <EnhancedDeckGLVisualization 
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
    </Box>
  );
}

function EnhancedDeckGLVisualization({ 
  points, 
  onPointHover, 
  onPointClick, 
  selectedClusterId,
  colorPalette = 'observable',
  showOutliers = true,
  pointSize = 10
}: {
  points: UMAPPoint[];
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
  colorPalette?: ColorPaletteName;
  showOutliers?: boolean;
  pointSize?: number;
}) {
  const [DeckGLComponent, setDeckGLComponent] = React.useState<any>(null);
  const [ScatterplotLayerComponent, setScatterplotLayerComponent] = React.useState<any>(null);
  const [HeatmapLayerComponent, setHeatmapLayerComponent] = React.useState<any>(null);
  const [PolygonLayerComponent, setPolygonLayerComponent] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [hoveredObject, setHoveredObject] = React.useState<UMAPPoint | null>(null);

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
        
        console.log('✅ DeckGL components loaded');
        setDeckGLComponent(() => deckModule.default);
        setScatterplotLayerComponent(() => layersModule.ScatterplotLayer);
        setHeatmapLayerComponent(() => aggModule.HeatmapLayer);
        setPolygonLayerComponent(() => layersModule.PolygonLayer);
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
        // Generate colorRange gradient from white to baseColor
        const colorRange = Array.from({ length: 6 }).map((_, idx) => {
          const t = idx / 5;
          const rgb = interpolateRgb(`rgb(${baseColor[0]},${baseColor[1]},${baseColor[2]})`, '#ffffff')(1 - t);
          const [r,g,b] = rgb.match(/\d+/g)!.map(Number);
          return [r, g, b, 255];
        });

        layerList.push(new HeatmapLayerComponent({
          id: `heatmap-${cid}`,
          data: pts,
          getPosition: (d: UMAPPoint) => [d.x, d.y],
          getWeight: 1,
          colorRange,
          radiusPixels: terrainResolution * 1.5,
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

    // Scatter layer
    if (showScatter) {
      const enhancedScatterplotLayer = new ScatterplotLayerComponent({
        id: 'umap-points',
        data: filteredPoints,
        pickable: true,
        stroked: true,
        lineWidthUnits: 'pixels',
        lineWidthMinPixels: 1,
        getLineColor: [0, 0, 0, 200],
        filled: true,
        radiusUnits: 'pixels',
        radiusMinPixels: effectivePointSize,
        getPosition: (d) => [d.x, d.y],
        getFillColor: (d) =>
          getEnhancedClusterColor(
            d,
            clusterStats.totalClusters,
            selectedClusterId ?? null,
            hoveredObject ? hoveredObject.id === d.id : false,
            effectiveColorPalette
          ),
        getRadius: effectivePointSize,
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
    <DeckGLComponent
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