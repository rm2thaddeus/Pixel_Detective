'use client';

import React, { useMemo, useEffect } from 'react';
import { Box, Spinner, Center, Text, VStack, Alert, AlertIcon } from '@chakra-ui/react';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';

// Lazy load DeckGL to avoid SSR issues
const DeckGL = React.lazy(() => import('@deck.gl/react'));
const ScatterplotLayer = React.lazy(() => import('@deck.gl/layers').then(module => ({ default: module.ScatterplotLayer })));

interface UMAPScatterPlotProps {
  data: UMAPProjectionResponse | null;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
}

// Calculate bounds for the points
function calculateBounds(points: UMAPPoint[]) {
  if (points.length === 0) return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
  
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  
  points.forEach(point => {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  });
  
  console.log('📏 Calculated bounds:', { minX, maxX, minY, maxY });
  return { minX, maxX, minY, maxY };
}

// Calculate initial view state to fit all points
function getInitialViewState(points: UMAPPoint[]) {
  const bounds = calculateBounds(points);
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  
  // Calculate zoom to fit all points with some padding
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const maxDimension = Math.max(width, height);
  
  // Base zoom calculation (adjust as needed)
  const zoom = maxDimension > 0 ? Math.log2(400 / maxDimension) : 5;
  
  const viewState = {
    longitude: centerX,
    latitude: centerY,
    zoom: Math.max(0, Math.min(zoom, 10)), // Clamp zoom between 0 and 10
    pitch: 0,
    bearing: 0,
  };
  
  console.log('🗺️ Initial view state:', viewState);
  return viewState;
}

export function UMAPScatterPlot({
  data,
  onPointHover,
  onPointClick,
  selectedClusterId,
}: UMAPScatterPlotProps) {

  // Debug logging
  useEffect(() => {
    console.log('🎨 UMAPScatterPlot render:', {
      hasData: !!data,
      pointsCount: data?.points?.length,
      selectedClusterId,
      firstPoint: data?.points?.[0],
      samplePoints: data?.points?.slice(0, 3),
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
          onPointHover={onPointHover}
          onPointClick={onPointClick}
          selectedClusterId={selectedClusterId}
        />
      </React.Suspense>
      
      {/* Debug overlay */}
      <Box position="absolute" top={2} left={2} bg="blackAlpha.700" color="white" px={2} py={1} borderRadius="md" fontSize="xs">
        {data.points.length} points loaded
      </Box>
      
      {/* Coordinates debug overlay */}
      <Box position="absolute" top={2} right={2} bg="blackAlpha.700" color="white" px={2} py={1} borderRadius="md" fontSize="xs">
        Sample: ({data.points[0]?.x.toFixed(2)}, {data.points[0]?.y.toFixed(2)})
      </Box>
    </Box>
  );
}

function SimpleDeckGLVisualization({ 
  points, 
  onPointHover, 
  onPointClick, 
  selectedClusterId 
}: {
  points: UMAPPoint[];
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
    return getInitialViewState(points);
  }, [points]);

  const layers = useMemo(() => {
    if (!ScatterplotLayerComponent) return [];

    console.log('🔧 Creating layer with', points.length, 'points');
    console.log('📍 First few points:', points.slice(0, 3).map(p => ({ id: p.id, x: p.x, y: p.y })));

    return [
      new ScatterplotLayerComponent({
        id: 'simple-scatterplot',
        data: points,
        getPosition: (d: UMAPPoint) => {
          const pos = [d.x, d.y, 0];
          if (points.indexOf(d) < 3) {
            console.log('📍 Point position for', d.id, ':', pos);
          }
          return pos;
        },
        getFillColor: [255, 100, 100, 200], // Bright red color for visibility
        getRadius: 10, // Larger radius for visibility
        radiusUnits: 'pixels',
        radiusMinPixels: 5,
        radiusMaxPixels: 20,
        pickable: true,
        onHover: (info: any) => {
          if (info.object) {
            console.log('🖱️ Point hover:', info.object.id, 'at', info.object.x, info.object.y);
          }
          onPointHover?.(info.object as UMAPPoint);
        },
        onClick: (info: any) => {
          if (info.object) {
            console.log('🖱️ Point click:', info.object.id, 'at', info.object.x, info.object.y);
          }
          onPointClick?.(info.object as UMAPPoint);
        },
      })
    ];
  }, [ScatterplotLayerComponent, points, onPointHover, onPointClick]);

  if (error) {
    return (
      <Center h="600px">
        <Alert status="error" maxW="md">
          <AlertIcon />
          <VStack align="start">
            <Text fontWeight="bold">DeckGL Error</Text>
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

  console.log('🎨 Rendering DeckGL with', layers.length, 'layers and view state:', initialViewState);

  return (
    <DeckGLComponent
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      width="100%"
      height="100%"
      onViewStateChange={({viewState}: any) => {
        console.log('🗺️ View state changed:', viewState);
      }}
      onLoad={() => {
        console.log('🎨 DeckGL loaded successfully');
      }}
      onError={(error: any) => {
        console.error('❌ DeckGL error:', error);
        setError(error.message || 'DeckGL rendering error');
      }}
      onAfterRender={() => {
        console.log('🎨 DeckGL rendered frame');
      }}
    />
  );
} 