'use client';

import { 
  Box, 
  Container, 
  Heading, 
  Text, 
  VStack, 
  Alert, 
  AlertIcon,
  Grid,
  GridItem,
  Spinner,
  Center,
  HStack
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { ClientOnly } from '@/components/ClientOnly';
import { useStore } from '@/store/useStore';
import { useLatentSpaceStore } from './hooks/useLatentSpaceStore';
import { useUMAP } from './hooks/useUMAP';
import React, { useEffect, useState } from 'react';

// Import the new components
import { UMAPScatterPlot } from './components/UMAPScatterPlot';
import { ClusteringControls } from './components/ClusteringControls';
import { MetricsPanel } from './components/MetricsPanel';
import { ClusterLabelingPanel } from './components/ClusterLabelingPanel';
import { ThumbnailOverlay } from './components/ThumbnailOverlay';
import { UMAPPoint } from './types/latent-space';

export default function LatentSpacePage() {
  const { collection } = useStore();
  const { 
    setProjectionData, 
    projectionData, 
    setSelectedCluster, 
    selectedCluster,
    selectedPoints,
    hoveredPoint,
    clusterLabels,
    setSelectedPoints,
    setHoveredPoint
  } = useLatentSpaceStore();

  const { basicProjection, isLoading, error } = useUMAP();

  const [mousePosition, setMousePosition] = useState<{ x: number, y: number } | null>(null);

  useEffect(() => {
    if (basicProjection.data) {
      setProjectionData(basicProjection.data);
    }
  }, [basicProjection.data, setProjectionData]);

  // Track mouse position for the overlay
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      setMousePosition({ x: event.clientX, y: event.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handlePointClick = (point: UMAPPoint) => {
    if (point.cluster_id !== undefined) {
      setSelectedCluster(point.cluster_id === selectedCluster ? null : point.cluster_id);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <Box p={6} minH="100vh">
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
      </Box>
    );
  }

  // Error state
  if (error) {
    return (
      <Box p={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <Text fontWeight="semibold">Failed to load latent space data</Text>
            <Text fontSize="sm">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  // No data state
  if (!basicProjection.data || !basicProjection.data.points || basicProjection.data.points.length === 0) {
    return (
      <Box p={6}>
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          <VStack align="start" spacing={2}>
            <Text fontWeight="semibold">No images found</Text>
            <Text fontSize="sm">
              Add some images to your collection to see them in the latent space visualization.
            </Text>
          </VStack>
        </Alert>
      </Box>
    );
  }

  const points = basicProjection.data.points;

  return (
    <ClientOnly>
      <Box minH="100vh">
        <Header />
        <Container maxW="full" p={6}>
          <VStack spacing={4} align="stretch">
            <Box>
              <Heading size="lg" mb={1}>Latent Space</Heading>
              <Text color="gray.600">
                Interactive 2D embedding space for collection analysis and auto-cataloging.
              </Text>
            </Box>
            <HStack spacing={6} align="start" flex={1}>
              <VStack spacing={4} w="300px" align="stretch">
                <ClusteringControls />
                <MetricsPanel />
                <ClusterLabelingPanel 
                  selectedPoints={selectedPoints}
                  clusterLabels={clusterLabels}
                />
              </VStack>
              <Box flex={1} h="600px" borderRadius="lg" overflow="hidden" boxShadow="md">
                <UMAPScatterPlot
                  data={basicProjection.data}
                  onPointHover={setHoveredPoint}
                  onPointClick={handlePointClick}
                  selectedClusterId={selectedCluster}
                />
              </Box>
            </HStack>
          </VStack>
        </Container>
      </Box>
      <ThumbnailOverlay point={hoveredPoint} mousePosition={mousePosition} />
    </ClientOnly>
  );
} 