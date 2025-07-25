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
  AspectRatio,
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
import { useUMAP, useUMAPZoom, fetchUMAPProjection } from './hooks/useUMAP';
import { useStreamingUMAP } from './hooks/useStreamingUMAP';
import { StreamingProgressMonitor } from './components/StreamingProgressMonitor';
import { useStore } from '@/store/useStore';
import { useLatentSpaceStore } from './hooks/useLatentSpaceStore';
import { UMAPPoint } from './types/latent-space';
import React, { useEffect } from 'react';
import { VisualizationBar } from './components/VisualizationBar';
import { ClusterLabelingPanel } from './components/ClusterLabelingPanel';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { archiveSelection } from '@/lib/api';
import { ClientOnly } from '@/components/ClientOnly';

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
  
  // Streaming UMAP functionality
  const { 
    startUMAPJob, 
    startClusteringJob,
    activeJobs, 
    cancelJob,
    hasActiveJobs,
    getJobStatus
  } = useStreamingUMAP();
  
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  
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
  const deckRef = React.useRef<HTMLElement>(null);
  const toast = useToast();

  // Handle streaming job results
  useEffect(() => {
    activeJobs.forEach(job => {
      if (job.status === 'completed' && job.result) {
        console.log(`Job ${job.job_id} completed successfully`);
        
        if (job.result.embeddings) {
          // UMAP job completed - convert embeddings to points
          const points = job.result.embeddings.map((embedding: number[], index: number) => ({
            id: `point_${index}`,
            position: embedding,
            x: embedding[0],
            y: embedding[1],
            cluster_id: undefined,
            is_outlier: false,
            metadata: {}
          }));
          
          // Update the store with new projection data
          useLatentSpaceStore.getState().setProjectionData({
            points,
            collection: collection || 'unknown',
            clustering_info: undefined
          });
          
          toast({
            title: 'UMAP Processing Complete',
            description: `Generated ${points.length} embeddings in ${job.processing_time.toFixed(1)}s`,
            status: 'success',
            duration: 5000,
            isClosable: true,
          });
        } else if (job.result.labels) {
          // Clustering job completed - apply labels to existing points
          const currentData = useLatentSpaceStore.getState().projectionData;
          if (currentData && currentData.points) {
            const updatedPoints = currentData.points.map((point, index) => ({
              ...point,
              cluster_id: job.result.labels[index],
              is_outlier: job.result.labels[index] === -1,
            }));
            
            const clusteringInfo = {
              algorithm: 'streaming',
              n_clusters: Object.keys(job.result.clusters || {}).length,
              silhouette_score: job.result.silhouette_score,
              n_outliers: job.result.labels.filter((l: number) => l === -1).length,
              parameters: {},
              clusters: job.result.clusters,
            };
            
            useLatentSpaceStore.getState().setProjectionData({
              ...currentData,
              points: updatedPoints,
              clustering_info: clusteringInfo
            });
            
            toast({
              title: 'Clustering Complete',
              description: `Found ${clusteringInfo.n_clusters} clusters in ${job.processing_time.toFixed(1)}s`,
              status: 'success',
              duration: 5000,
              isClosable: true,
            });
          }
        }
      } else if (job.status === 'failed') {
        toast({
          title: 'Processing Failed',
          description: job.error || 'An error occurred during processing',
          status: 'error',
          duration: 10000,
          isClosable: true,
        });
      }
    });
  }, [activeJobs, collection, toast]);

  // Handle large dataset processing
  const handleLargeDatasetProcessing = async (data: number[][], isUMAP: boolean = true) => {
    try {
      if (isUMAP) {
        const result = await startUMAPJob.mutateAsync({
          data,
          n_components: 2,
          n_neighbors: 15,
          min_dist: 0.1,
          metric: "cosine",
          random_state: 42
        });
        
        if (result.job_id === 'immediate') {
          // Small dataset - result is already available
          const job = getJobStatus('immediate');
          if (job?.result?.embeddings) {
            const points = job.result.embeddings.map((embedding: number[], index: number) => ({
              id: `point_${index}`,
              position: embedding,
              x: embedding[0],
              y: embedding[1],
              cluster_id: undefined,
              is_outlier: false,
              metadata: {}
            }));
            
            useLatentSpaceStore.getState().setProjectionData({
              points,
              collection: collection || 'unknown',
              clustering_info: undefined
            });
          }
        } else {
          toast({
            title: 'UMAP Processing Started',
            description: `Processing ${data.length} points in background`,
            status: 'info',
            duration: 3000,
            isClosable: true,
          });
        }
      } else {
        // Clustering
        const result = await startClusteringJob.mutateAsync({
          data,
          algorithm: clusteringParams.algorithm || 'dbscan',
          n_clusters: clusteringParams.n_clusters,
          eps: clusteringParams.eps,
          min_samples: clusteringParams.min_samples,
          min_cluster_size: clusteringParams.min_cluster_size
        });
        
        if (result.job_id === 'immediate') {
          // Small dataset - result is already available
          const job = getJobStatus('immediate');
          if (job?.result?.labels) {
            const currentData = useLatentSpaceStore.getState().projectionData;
            if (currentData && currentData.points) {
              const updatedPoints = currentData.points.map((point, index) => ({
                ...point,
                cluster_id: job.result.labels[index],
                is_outlier: job.result.labels[index] === -1,
              }));
              
              const clusteringInfo = {
                algorithm: clusteringParams.algorithm || 'dbscan',
                n_clusters: Object.keys(job.result.clusters || {}).length,
                silhouette_score: job.result.silhouette_score,
                n_outliers: job.result.labels.filter((l: number) => l === -1).length,
                parameters: clusteringParams,
                clusters: job.result.clusters,
              };
              
              useLatentSpaceStore.getState().setProjectionData({
                ...currentData,
                points: updatedPoints,
                clustering_info: clusteringInfo
              });
            }
          }
        } else {
          toast({
            title: 'Clustering Started',
            description: `Processing ${data.length} points in background`,
            status: 'info',
            duration: 3000,
            isClosable: true,
          });
        }
      }
    } catch (error) {
      console.error('Failed to start processing:', error);
      toast({
        title: 'Processing Failed',
        description: 'Failed to start background processing',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
    onSettled: onClose,
  });

  const loadAllMutation = useMutation({
    mutationFn: () => fetchUMAPProjection(collection, 5000, undefined, true),
    onSuccess: (data) => {
      useLatentSpaceStore.getState().setProjectionData(data);
    },
  });

  const handleArchive = () => {
    archiveMutation.mutate(Array.from(selectedIds));
  };

  const handleLoadAll = () => {
    loadAllMutation.mutate();
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
      !clusteringMutation.isSuccess &&
      !hasActiveJobs()
    ) {
      console.info('[LatentSpacePage] Auto-triggering initial clustering run');
      
      // Check if we should use streaming for large datasets
      if (basicProjection.data.points.length > 1000) {
        // Use streaming for large datasets
        const dataForApi = basicProjection.data.points.map(p => [p.x, p.y]);
        handleLargeDatasetProcessing(dataForApi, false);
      } else {
        // Use traditional approach for small datasets
        clusteringMutation.mutate({
          ...clusteringParams,
          points: basicProjection.data.points,
        }, {
          onSuccess: (data) => {
            useLatentSpaceStore.getState().setProjectionData(data);
          },
        });
      }
    }
  }, [basicProjection.data, clusteringParams, clusteringMutation, hasActiveJobs]);

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
        <ClientOnly>
          <Header />
        </ClientOnly>
        <Container maxW="6xl" p={6}>
          <VStack spacing={8} align="center" justify="center" minH="60vh">
            <Alert status="info" borderRadius="lg">
              <AlertIcon />
              <VStack align="start" spacing={2}>
                <Text fontWeight="semibold">No Collection Selected</Text>
                <Text fontSize="sm">
                  Please select a collection to view the latent space visualization.
                </Text>
              </VStack>
            </Alert>
          </VStack>
        </Container>
      </Box>
    );
  }

  if (error) {
    return (
      <Box minH="100vh">
        <ClientOnly>
          <Header />
        </ClientOnly>
        <Container maxW="6xl" p={6}>
          <VStack spacing={8} align="center" justify="center" minH="60vh">
            <Alert status="error" borderRadius="lg">
              <AlertIcon />
              <VStack align="start" spacing={2}>
                <Text fontWeight="semibold">Failed to Load Visualization</Text>
                <Text fontSize="sm">
                  {error.message || 'An error occurred while loading the UMAP projection.'}
                </Text>
              </VStack>
            </Alert>
          </VStack>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh">
      <ClientOnly>
        <Header />
      </ClientOnly>

      <Container maxW="6xl" p={6}>
        <VStack spacing={6} align="stretch">
          {/* Page Header */}
          <Box>
            <Text fontSize="2xl" fontWeight="bold" mb={2}>
              Latent Space Visualization
            </Text>
            <Text color="gray.600" fontSize="sm">
              Explore your image collection through UMAP dimensionality reduction and clustering analysis.
            </Text>
          </Box>

          {/* Loading State */}
          {isLoading && !effectiveProjection && (
            <VStack spacing={4} py={12}>
              <Spinner size="xl" />
              <Text>Loading visualization...</Text>
            </VStack>
          )}

          {/* Main Visualization */}
          {effectiveProjection && (
            <Flex direction="column" gap={4}>
              <Flex direction={{ base: 'column', lg: 'row' }} gap={4}>
                {/* UMAP Plot */}
                <AspectRatio ratio={1} flex="1" w="100%" onMouseEnter={() => setShowControls(true)}>
                  <Box
                    position="relative"
                    borderRadius="lg"
                    overflow="hidden"
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
                  </Box>
                </AspectRatio>

                {/* Persistent controls column (desktop) */}
                <Box display={{ base: 'none', lg: 'block' }} w="240px" flexShrink={0}>
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
            {/* Stats Bar */}
            <StatsBar
              stats={effectiveProjection.clustering_info}
              totalPoints={effectiveProjection.points.length}
            />
            <Button size="sm" onClick={handleLoadAll} alignSelf="start">
              Load all points
            </Button>

              {/* Cluster Labeling Panel */}
              <ClusterLabelingPanel
                points={effectiveProjection.points}
                selectedClusterId={selectedCluster}
                colorPalette={colorPalette}
              />
            </Flex>
          )}
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