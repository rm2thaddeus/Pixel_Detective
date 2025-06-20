'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { Box, Spinner, Center, Text, VStack, Alert, AlertIcon } from '@chakra-ui/react';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';
import { getClusterColor, getOptimalViewState, calculateBounds } from '../utils/visualization';

// Lazy load DeckGL to avoid SSR issues
const DeckGL = React.lazy(() => import('@deck.gl/react'));
const ScatterplotLayer = React.lazy(() => import('@deck.gl/layers').then(module => ({ default: module.ScatterplotLayer })));

interface UMAPScatterPlotProps {
  data: UMAPProjectionResponse | null;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
}

// Note: Utility functions moved to utils/visualization.ts

export function UMAPScatterPlot({
  data,
  onPointHover,
  onPointClick,
  selectedClusterId,
}: UMAPScatterPlotProps) {
  const [hoveredPoint, setHoveredPoint] = useState<UMAPPoint | null>(null);

  // Debug logging
  useEffect(() => {
    console.log('🎨 UMAPScatterPlot render:', {
      hasData: !!data,
      pointsCount: data?.points?.length,
      selectedClusterId,
      firstPoint: data?.points?.[0],
      samplePoints: data?.points?.slice(0, 3),
      clusteringInfo: data?.clustering_info,
    });
  }, [data, selectedClusterId]);

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
    <Box position="relative" h="600px" bg="white" borderRadius="md" border="1px solid" borderColor="gray.200">
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
        <SimpleDeckGLVisualization 
          points={data.points} 
          clusteringInfo={data.clustering_info}
          onPointHover={(point) => {
            setHoveredPoint(point);
            onPointHover?.(point);
          }}
          onPointClick={onPointClick}
          selectedClusterId={selectedClusterId}
        />
      </React.Suspense>
      
      {/* Info overlays */}
      <Box position="absolute" top={2} left={2} bg="blackAlpha.700" color="white" px={2} py={1} borderRadius="md" fontSize="xs">
        {data.points.length} points • {data.clustering_info?.n_clusters || 0} clusters
      </Box>
      
      {hoveredPoint && (
        <Box position="absolute" top={2} right={2} bg="blackAlpha.800" color="white" px={3} py={2} borderRadius="md" fontSize="xs" maxW="200px">
          <Text fontWeight="bold">{hoveredPoint.filename || hoveredPoint.id}</Text>
          <Text>Cluster: {hoveredPoint.cluster_id ?? 'None'}</Text>
          <Text>Position: ({hoveredPoint.x.toFixed(2)}, {hoveredPoint.y.toFixed(2)})</Text>
          {hoveredPoint.is_outlier && <Text color="red.300">Outlier</Text>}
        </Box>
      )}
    </Box>
  );
}

function SimpleDeckGLVisualization({ 
  points, 
  clusteringInfo,
  onPointHover, 
  onPointClick, 
  selectedClusterId 
}: {
  points: UMAPPoint[];
  clusteringInfo?: any;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
}) {
  const [DeckGLComponent, setDeckGLComponent] = React.useState<any>(null);
  const [ScatterplotLayerComponent, setScatterplotLayerComponent] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  useEffect(() => {
    const loadComponents = async () => {
      try {
        console.log('📦 Loading DeckGL components...');
        
        const deckModule = await import('@deck.gl/react');
        const layersModule = await import('@deck.gl/layers');
        
        console.log('✅ DeckGL components loaded');
        setDeckGLComponent(() => deckModule.default);
        setScatterplotLayerComponent(() => layersModule.ScatterplotLayer);
      } catch (err) {
        console.error('❌ Failed to load DeckGL:', err);
        setError(err instanceof Error ? err.message : 'Failed to load DeckGL');
      }
    };

    loadComponents();
  }, []);

  const initialViewState = useMemo(() => {
    return getOptimalViewState(points);
  }, [points]);

  const layers = useMemo(() => {
    if (!ScatterplotLayerComponent) return [];

    console.log('🔧 Creating layer with', points.length, 'points');
    console.log('📍 First few points:', points.slice(0, 3).map(p => ({ id: p.id, x: p.x, y: p.y, cluster_id: p.cluster_id })));

    const totalClusters = clusteringInfo?.n_clusters || Math.max(...points.map(p => p.cluster_id || 0)) + 1;

    return [
      new ScatterplotLayerComponent({
        id: 'clustered-scatterplot',
        data: points,
        getPosition: (d: UMAPPoint) => {
          const pos = [d.x, d.y, 0];
          return pos;
        },
        getFillColor: (d: UMAPPoint) => {
          const baseColor = getClusterColor(d, totalClusters);
          
          // Highlight selected cluster
          if (selectedClusterId !== null && selectedClusterId !== undefined) {
            if (d.cluster_id === selectedClusterId) {
              return [baseColor[0], baseColor[1], baseColor[2], 255]; // Full opacity
            } else {
              return [baseColor[0], baseColor[1], baseColor[2], 100]; // Dimmed
            }
          }
          
          return baseColor;
        },
        getRadius: (d: UMAPPoint) => {
          // Slightly larger radius for selected cluster or outliers
          if (d.is_outlier) return 12;
          if (selectedClusterId !== null && d.cluster_id === selectedClusterId) return 14;
          return 10;
        },
        radiusUnits: 'pixels',
        radiusMinPixels: 5,
        radiusMaxPixels: 25,
        pickable: true,
        onHover: (info: any) => {
          if (info.object) {
            console.log('🖱️ Point hover:', info.object.id, 'cluster:', info.object.cluster_id);
            onPointHover?.(info.object);
          } else {
            onPointHover?.(null);
          }
        },
        onClick: (info: any) => {
          if (info.object) {
            console.log('🖱️ Point click:', info.object.id, 'cluster:', info.object.cluster_id);
            onPointClick?.(info.object);
          }
        },
        updateTriggers: {
          getFillColor: [selectedClusterId, totalClusters],
          getRadius: [selectedClusterId],
        },
      }),
    ];
  }, [ScatterplotLayerComponent, points, selectedClusterId, clusteringInfo, onPointHover, onPointClick]);

  if (error) {
    return (
      <Center h="600px">
        <Alert status="error">
          <AlertIcon />
          <VStack align="start">
            <Text>Failed to load DeckGL</Text>
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
          <Spinner size="xl" />
          <Text>Loading DeckGL components...</Text>
        </VStack>
      </Center>
    );
  }

  return (
    <DeckGLComponent
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      style={{ width: '100%', height: '100%' }}
      getCursor={({ isDragging, isHovering }) => {
        if (isDragging) return 'grabbing';
        if (isHovering) return 'pointer';
        return 'grab';
      }}
    />
  );
} 