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
  HStack
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { UMAPScatterPlot } from './components/UMAPScatterPlot';
import { useUMAP } from './hooks/useUMAP';
import { useStore } from '@/store/useStore';
import React, { useEffect } from 'react';

export default function LatentSpacePage() {
  const { collection } = useStore();
  const { basicProjection, isLoading, error } = useUMAP();
  const [debugInfo, setDebugInfo] = useState<any>({});

  // Debug logging
  useEffect(() => {
    const info = {
      collection,
      isLoading,
      error: error?.message,
      hasData: !!basicProjection.data,
      pointsCount: basicProjection.data?.points?.length,
      timestamp: new Date().toISOString(),
    };
    
    console.log('🔍 Latent Space Debug:', info);
    setDebugInfo(info);
  }, [collection, isLoading, error, basicProjection.data]);

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
  if (!basicProjection.data || !basicProjection.data.points || basicProjection.data.points.length === 0) {
    console.warn('⚠️ No data available:', {
      hasBasicProjection: !!basicProjection.data,
      hasPoints: !!basicProjection.data?.points,
      pointsLength: basicProjection.data?.points?.length,
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

  const points = basicProjection.data.points;
  console.log('✅ Rendering latent space with', points.length, 'points');

  return (
    <Box minH="100vh">
      <Header />
      <Container maxW="full" p={6}>
        <VStack spacing={4} align="stretch">
          <Box>
            <Text fontSize="2xl" fontWeight="bold" mb={1}>Latent Space Visualization</Text>
            <Text color="gray.600">
              Interactive 2D embedding space for collection analysis.
            </Text>
            <Text fontSize="sm" color="blue.500" mt={2}>
              Debug: {points.length} points loaded from collection "{collection || 'default'}"
            </Text>
          </Box>

          {/* Debug Info Panel */}
          <Box bg="gray.50" p={3} borderRadius="md" fontSize="xs">
            <Text fontWeight="bold" mb={2}>Debug Information:</Text>
            <pre>{JSON.stringify(debugInfo, null, 2)}</pre>
          </Box>

          {/* Main Visualization */}
          <Box>
            <Text fontSize="lg" fontWeight="semibold" mb={4}>Visualization</Text>
            <Box h="600px" borderRadius="lg" overflow="hidden" boxShadow="md">
              <UMAPScatterPlot
                data={basicProjection.data}
                onPointHover={(point) => console.log('Point hovered:', point?.id)}
                onPointClick={(point) => console.log('Point clicked:', point?.id)}
              />
            </Box>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
} 