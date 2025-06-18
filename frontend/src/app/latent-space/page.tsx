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
  Center
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
    selectedCluster 
  } = useLatentSpaceStore();

  const { basicProjection, isLoading, error } = useUMAP(2000); // Increase sample size

  const [hoveredPoint, setHoveredPoint] = useState<UMAPPoint | null>(null);
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

  const renderContent = () => {
    if (!collection) {
      return (
        <Alert status="warning" mt={6}>
          <AlertIcon />
          Please select a collection to visualize its latent space representation.
        </Alert>
      );
    }

    if (isLoading) {
      return (
        <Center h="50vh">
          <VStack>
            <Spinner size="xl" />
            <Text>Loading and projecting {collection}...</Text>
          </VStack>
        </Center>
      );
    }

    if (error) {
      return (
        <Alert status="error" mt={6}>
          <AlertIcon />
          Error loading projection: {error.message}
        </Alert>
      );
    }
    
    if (projectionData) {
      return (
        <Grid
          templateAreas={`"main sidebar"`}
          templateColumns={'3fr 1fr'}
          gap={6}
          h="calc(100vh - 200px)"
        >
          <GridItem area="main" position="relative">
            <UMAPScatterPlot 
              data={projectionData}
              onPointHover={setHoveredPoint}
              onPointClick={handlePointClick}
              selectedClusterId={selectedCluster}
            />
          </GridItem>
          <GridItem area="sidebar" overflowY="auto" >
            <VStack spacing={6} align="stretch">
              <ClusteringControls />
              <MetricsPanel 
                clusteringInfo={projectionData.clustering_info}
                totalPoints={projectionData.points.length}
              />
              <ClusterLabelingPanel />
            </VStack>
          </GridItem>
        </Grid>
      );
    }

    return null;
  };

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
            {renderContent()}
          </VStack>
        </Container>
      </Box>
      <ThumbnailOverlay point={hoveredPoint} mousePosition={mousePosition} />
    </ClientOnly>
  );
} 