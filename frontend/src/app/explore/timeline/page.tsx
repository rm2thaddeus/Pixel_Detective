'use client';

import { Box, Heading, VStack, Input, Text } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFeatureEvolution } from '@/lib/api';
import { EnhancedTimeline } from '@/components/explore/EnhancedTimeline';

export default function TimelinePage() {
  const [feature, setFeature] = useState('Streaming UMAP');
  const { data } = useQuery({
    queryKey: ['feature-evolution', feature],
    queryFn: () => fetchFeatureEvolution(feature),
  });

  return (
    <Box minH="100vh">
      <Header />
      <Box maxW="6xl" mx="auto" p={8}>
        <VStack align="start" spacing={6}>
          <Heading size="lg">Time Travel</Heading>
          <Input value={feature} onChange={(e) => setFeature(e.target.value)} placeholder="Feature name" />
          {data ? (
            <EnhancedTimeline events={data.events} />
          ) : (
            <Text color="gray.500">Loading timeline...</Text>
          )}
        </VStack>
      </Box>
    </Box>
  );
}

