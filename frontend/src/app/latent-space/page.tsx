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
  Divider,
  Collapse,
  Flex,
  Button,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useToast
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { UMAPScatterPlot } from './components/UMAPScatterPlot';
import { ClusteringControls } from './components/ClusteringControls';
import { ThumbnailOverlay } from './components/ThumbnailOverlay';
import { StatsBar } from './components/StatsBar';
import { useUMAP } from './hooks/useUMAP';
import { useStore } from '@/store/useStore';
import { useLatentSpaceStore } from './hooks/useLatentSpaceStore';
import { UMAPPoint } from './types/latent-space';
import React, { useEffect } from 'react';
import { VisualizationBar } from './components/VisualizationBar';
import { ClusterLabelingPanel } from './components/ClusterLabelingPanel';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { archiveSelection } from '@/lib/api';

export default function LatentSpacePage() {
  const { collection } = useStore();

  // ------------------------------------------------------------------
  // 1️⃣  Reset local latent-space visualisation state when the user switches
  //     active collection.  Without this the previously stored projection
  //     persists in Zustand and overrides freshly-fetched data, so the
  //     scatter plot never updates.  We keep a ref of the last collection
  //     to detect changes and avoid resetting on initial mount.
  // ------------------------------------------------------------------

  const lastCollectionRef = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (lastCollectionRef.current === null) {
      // First render – just record the initial collection.
      lastCollectionRef.current = collection;
      return;
    }

    if (collection !== lastCollectionRef.current) {
      console.info('[LatentSpacePage] Active collection changed → resetting state');
      useLatentSpaceStore.getState().resetState();
      lastCollectionRef.current = collection;
    }
  }, [collection]);

  // Use an adaptive sample size (1 000) to balance detail and API latency.
  const { basicProjection, isLoading, error, clusteringMutation } = useUMAP(1000);
  const { 
    selectedCluster, 
    setSelectedCluster,
    colorPalette,
    showOutliers,
    pointSize,
    clusteringParams,
    selectedIds,
    setSelectedIds,
  } = useLatentSpaceStore();
  const [hoveredPoint, setHoveredPoint] = useState<UMAPPoint | null>(null);
  const [mousePosition, setMousePosition] = useState<{ x: number; y: number } | null>(null);
  const [showControls, setShowControls] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const cancelRef = React.useRef<HTMLButtonElement | null>(null);
  const deckRef = React.useRef<HTMLElement>(null); // For export functionality
  const toast = useToast();
  const queryClient = useQueryClient();

  const archiveMutation = useMutation({
    mutationFn: (pointIds: string[]) => archiveSelection(pointIds),
    onSuccess: () => {
      toast({
        title: 'Selection archived.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ['umap', collection] }); // Refetch UMAP data
    },
    onError: (err: Error) => {
      toast({
        title: 'Archiving failed.',
        description: err.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
    onSettled: onClose,
  });

  const handleArchive = () => {
    archiveMutation.mutate(Array.from(selectedIds));
  };

  const debugInfo = {
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

  // Log once per relevant change
  useEffect(() => {
    console.log('🔍 Latent Space Debug:', debugInfo);
  }, [debugInfo]);

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
  const storedProjectionData = useLatentSpaceStore((s) => s.projectionData);

  const effectiveProjection = storedProjectionData ?? basicProjection.data;

  // Hotkey: ⌘/Ctrl + K toggles clustering controls
  useEffect(() => {
    const keyHandler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setShowControls((prev) => !prev);
      }
    };
    window.addEventListener('keydown', keyHandler);
    return () => window.removeEventListener('keydown', keyHandler);
  }, []);

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
            </VStack>
          </Alert>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh">
      <Header />
      <AlertDialog isOpen={isOpen} leastDestructiveRef={cancelRef} onClose={onClose}>
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader>Archive Selection</AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to archive {selectedIds.size} selected images?
              This action is reversible from the filesystem, but will remove the items from the database.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onClose}>Cancel</Button>
              <Button colorScheme="red" onClick={handleArchive} ml={3} isLoading={archiveMutation.isPending}>
                Archive
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
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
            {selectedIds.size > 0 && (
              <HStack>
                <Text color="red.500" fontWeight="bold">
                  {selectedIds.size} points selected
                </Text>
                <Button size="sm" colorScheme="red" onClick={onOpen}>
                  Archive Selection
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
                  Clear Selection
                </Button>
              </HStack>
            )}
          </Box>

          <Divider />

          {/* === Compact Vertical Layout === */}
          <Flex direction="column" gap={4}>
            <Flex direction={{ base: 'column', lg: 'row' }} gap={4}>
              {/* UMAP Plot */}
              <Box
                position="relative"
                flex="1 1 auto"
                h={{ base: '60vh', md: '70vh' }}
                borderRadius="lg"
                overflow="hidden"
                onMouseEnter={() => setShowControls(true)}
              >
                <UMAPScatterPlot
                  data={effectiveProjection}
                  onPointHover={handlePointHover}
                  onPointClick={handlePointClick}
                  selectedClusterId={selectedCluster}
                  colorPalette={colorPalette}
                  showOutliers={showOutliers}
                  pointSize={pointSize}
                  deckRef={deckRef}
                />

                {/* Mobile collapsible toolbar */}
                <Box position="absolute" top={0} left={0} w="full" display={{ base: 'block', lg: 'none' }}>
                  <Collapse in={showControls} animateOpacity>
                    <Box bg="whiteAlpha.900" _dark={{ bg: 'gray.800' }} p={2} shadow="md">
                      <ClusteringControls 
                        variant="compact" 
                        deckRef={deckRef}
                        selectedClusterId={selectedCluster}
                      />
                    </Box>
                  </Collapse>
                </Box>
              </Box>

              {/* Persistent controls column (desktop) */}
              <Box display={{ base: 'none', lg: 'block' }} w="320px" flexShrink={0}>
                <ClusteringControls 
                  variant="compact" 
                  deckRef={deckRef}
                  selectedClusterId={selectedCluster}
                />
              </Box>
            </Flex>

            {/* Visualization Settings Bar */}
            <VisualizationBar />

            {/* Stats Bar */}
            <StatsBar
              stats={effectiveProjection.clustering_info}
              totalPoints={effectiveProjection.points.length}
            />

            {/* Cluster Labeling Panel */}
            <ClusterLabelingPanel
              points={effectiveProjection.points}
              selectedClusterId={selectedCluster}
              colorPalette={colorPalette}
            />
          </Flex>
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