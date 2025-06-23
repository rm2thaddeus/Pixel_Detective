'use client';

import { useState } from 'react';
import { 
  Box, 
  Container, 
  VStack, 
  Text, 
  Alert, 
  AlertIcon, 
  Spinner,
  HStack,
  Grid,
  GridItem,
  Divider
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { UMAPScatterPlot } from './components/UMAPScatterPlot';
import { ClusteringControls } from './components/ClusteringControls';
import { MetricsPanel } from './components/MetricsPanel';
import { ThumbnailOverlay } from './components/ThumbnailOverlay';
import { ClusterLabelingPanel } from './components/ClusterLabelingPanel';
import { useUMAP } from './hooks/useUMAP';
import { useStore } from '@/store/useStore';
import { useLatentSpaceStore } from './hooks/useLatentSpaceStore';
import { UMAPPoint } from './types/latent-space';
import React, { useEffect } from 'react';

export default function LatentSpacePage() {
  const { collection } = useStore();
  const { basicProjection, isLoading, error, clusteringMutation } = useUMAP();
  const { 
    selectedCluster, 
    setSelectedCluster,
    colorPalette,
    showOutliers,
    pointSize,
    clusteringParams
  } = useLatentSpaceStore();
  const [hoveredPoint, setHoveredPoint] = useState<UMAPPoint | null>(null);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);
  const [debugInfo, setDebugInfo] = useState<Record<string, unknown>>({});

  // Debug logging
  useEffect(() => {
    const info = {
      collection,
      isLoading,
      error: error?.message,
      hasData: !!basicProjection.data,
      pointsCount: basicProjection.data?.points?.length,
      clusteringInfo: basicProjection.data?.clustering_info,
      selectedCluster,
      colorPalette,
      showOutliers,
      pointSize,
      timestamp: new Date().toISOString(),
    };
    
    console.log('🔍 Latent Space Debug:', info);
    setDebugInfo(info);
  }, [collection, isLoading, error, basicProjection.data, selectedCluster, colorPalette, showOutliers, pointSize]);

  // Handle mouse movement for thumbnail overlay
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
    };

    if (hoveredPoint) {
      document.addEventListener('mousemove', handleMouseMove);
      return () => document.removeEventListener('mousemove', handleMouseMove);
    }
  }, [hoveredPoint]);

  const handlePointHover = (point: UMAPPoint | null) => {
    setHoveredPoint(point);
    if (!point) {
      setMousePosition(null);
    }
  };

  const handlePointClick = (point: UMAPPoint) => {
    console.log('🖱️ Point clicked:', point);
    if (point.cluster_id !== undefined && point.cluster_id !== null) {
      setSelectedCluster(selectedCluster === point.cluster_id ? null : point.cluster_id);
    }
  };

  // Auto-run clustering once we have a fresh projection but no clustering yet
  useEffect(() => {
    if (
      basicProjection.data?.points?.length &&
      !basicProjection.data?.clustering_info &&
      !clusteringMutation.isPending &&
      !clusteringMutation.isSuccess
    ) {
      console.info('[LatentSpacePage] Auto-triggering initial clustering run');
      clusteringMutation.mutate({
        ...clusteringParams,
        points: basicProjection.data.points,
      }, {
        onSuccess: (data) => {
          useLatentSpaceStore.getState().setProjectionData(data);
        },
      });
    }
  }, [basicProjection.data, clusteringParams, clusteringMutation]);

  // Prefer the projection data that may have been stored after clusteringMutation
  const { projectionData: storedProjectionData } = useLatentSpaceStore();

  const effectiveProjection = storedProjectionData ?? basicProjection.data;

  // Loading state
  if (isLoading) {
    return (
      <Box minH="100vh">
        <Header />
        <Container maxW="full" p={6}>
          <VStack spacing={6} align="center" justify="center" minH="60vh">
            <Spinner size="xl" color="purple.500" thickness="4px" />
            <VStack spacing={2}>
              <Text fontSize="lg" fontWeight="semibold">
                Loading Latent Space Visualization
              </Text>
              <Text color="gray.600" textAlign="center" maxW="md">
                Fetching embeddings and computing 2D projections...
                <br />
                This may take a few moments for large collections.
              </Text>
            </VStack>
          </VStack>
        </Container>
      </Box>
    );
  }

  // Error state
  if (error) {
    console.error('❌ Latent Space Error:', error);
    return (
      <Box minH="100vh">
        <Header />
        <Container maxW="full" p={6}>
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <VStack align="start" spacing={2}>
              <Text fontWeight="semibold">Failed to load latent space data</Text>
              <Text fontSize="sm">
                {error instanceof Error ? error.message : 'Unknown error occurred'}
              </Text>
              <Text fontSize="xs" color="gray.500">
                Debug: {JSON.stringify(debugInfo, null, 2)}
              </Text>
            </VStack>
          </Alert>
        </Container>
      </Box>
    );
  }

  // No data state
  if (!effectiveProjection || !effectiveProjection.points || effectiveProjection.points.length === 0) {
    console.warn('⚠️ No data available:', {
      hasProjection: !!effectiveProjection,
      hasPoints: !!effectiveProjection?.points,
      pointsLength: effectiveProjection?.points?.length,
    });
    return (
      <Box minH="100vh">
        <Header />
        <Container maxW="full" p={6}>
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <VStack align="start" spacing={2}>
              <Text fontWeight="semibold">No images found</Text>
              <Text fontSize="sm">
                Add some images to your collection to see them in the latent space visualization.
              </Text>
              <Text fontSize="xs" color="gray.500">
                Debug: {JSON.stringify(debugInfo, null, 2)}
              </Text>
            </VStack>
          </Alert>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh">
      <Header />
      <Container maxW="full" p={6}>
        <VStack spacing={6} align="stretch">
          {/* Header Section */}
          <Box>
            <Text fontSize="2xl" fontWeight="bold" mb={1}>Latent Space Visualization</Text>
            <Text color="gray.600">
              Interactive 2D embedding space for collection analysis and clustering.
            </Text>
            <HStack spacing={4} mt={2} fontSize="sm">
              <Text color="blue.500">
                {effectiveProjection.points.length} points • {effectiveProjection.clustering_info?.n_clusters || 0} clusters
              </Text>
              {effectiveProjection.clustering_info?.algorithm && (
                <Text color="green.500">
                  Algorithm: {effectiveProjection.clustering_info.algorithm}
                </Text>
              )}
              {selectedCluster !== null && (
                <Text color="purple.500">
                  Selected cluster: {selectedCluster}
                </Text>
              )}
            </HStack>
          </Box>

          <Divider />

          {/* Main Content Grid */}
          <Grid templateColumns={{ base: "1fr", lg: "1fr 300px" }} gap={6}>
            
            {/* Main Visualization */}
            <GridItem>
              <VStack spacing={4} align="stretch">
                <Box>
                  <Text fontSize="lg" fontWeight="semibold" mb={4}>
                    Cluster Visualization
                  </Text>
                  <Box h="600px" borderRadius="lg" overflow="hidden" boxShadow="md">
                    <UMAPScatterPlot
                      data={effectiveProjection}
                      onPointHover={handlePointHover}
                      onPointClick={handlePointClick}
                      selectedClusterId={selectedCluster}
                      colorPalette={colorPalette}
                      showOutliers={showOutliers}
                      pointSize={pointSize}
                    />
                  </Box>
                </Box>
                
                {/* Instructions */}
                <Box bg="blue.50" p={4} borderRadius="md" fontSize="sm">
                  <Text fontWeight="semibold" mb={2}>💡 Interaction Guide:</Text>
                  <VStack align="start" spacing={1}>
                    <Text>• <strong>Hover</strong> over points to see image details</Text>
                    <Text>• <strong>Click</strong> points to select/deselect clusters</Text>
                    <Text>• <strong>Drag</strong> to pan and <strong>scroll</strong> to zoom</Text>
                    <Text>• Outliers are highlighted in red</Text>
                  </VStack>
                </Box>
              </VStack>
            </GridItem>

            {/* Controls and Metrics Sidebar */}
            <GridItem>
              <VStack spacing={6} align="stretch">
                
                {/* Clustering Controls */}
                <ClusteringControls />
                
                {/* Cluster Labeling Panel */}
                <ClusterLabelingPanel 
                  points={effectiveProjection.points}
                  selectedClusterId={selectedCluster}
                  colorPalette={colorPalette}
                />
                
                {/* Metrics Panel */}
                <MetricsPanel 
                  clusteringInfo={effectiveProjection.clustering_info}
                  totalPoints={effectiveProjection.points.length}
                  points={effectiveProjection.points}
                />
                
                {/* Debug Panel - Remove in production */}
                <Box bg="gray.50" p={3} borderRadius="md" fontSize="xs">
                  <Text fontWeight="bold" mb={2}>Debug Information:</Text>
                  <Box as="pre" overflow="auto" maxH="200px">
                    {JSON.stringify({
                      collection: collection || 'default',
                      pointsCount: effectiveProjection.points.length,
                      clusteringInfo: effectiveProjection.clustering_info,
                      selectedCluster,
                      hoveredPoint: hoveredPoint?.id || null,
                      colorPalette,
                      showOutliers,
                      pointSize,
                    }, null, 2)}
                  </Box>
                </Box>
                
              </VStack>
            </GridItem>
            
          </Grid>
        </VStack>
      </Container>

      {/* Thumbnail Overlay */}
      <ThumbnailOverlay
        point={hoveredPoint}
        mousePosition={mousePosition}
        onImageClick={handlePointClick}
      />
    </Box>
  );
} 