'use client';

import { Box, VStack, Text, Stat, StatLabel, StatNumber, StatHelpText, SimpleGrid, useColorModeValue, Alert, AlertIcon } from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';

export function RealAnalytics({ fromTimestamp, toTimestamp }: { fromTimestamp?: string; toTimestamp?: string }) {
  const bg = useColorModeValue('white', 'gray.800');
  const border = useColorModeValue('gray.200', 'gray.600');
  const base = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8000';

  const { data: activity, isLoading: loadingA, error: errorA } = useQuery({
    queryKey: ['analytics', 'activity', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (fromTimestamp) params.set('from_timestamp', fromTimestamp);
      if (toTimestamp) params.set('to_timestamp', toTimestamp);
      const res = await fetch(`${base}/api/v1/analytics/activity?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to load activity analytics');
      return res.json();
    },
    staleTime: 60_000,
  });

  const { data: graph, isLoading: loadingG, error: errorG } = useQuery({
    queryKey: ['analytics', 'graph', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (fromTimestamp) params.set('from_timestamp', fromTimestamp);
      if (toTimestamp) params.set('to_timestamp', toTimestamp);
      const res = await fetch(`${base}/api/v1/analytics/graph?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to load graph analytics');
      return res.json();
    },
    staleTime: 60_000,
  });

  const { data: trace, isLoading: loadingT, error: errorT } = useQuery({
    queryKey: ['analytics', 'traceability', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (fromTimestamp) params.set('from_timestamp', fromTimestamp);
      if (toTimestamp) params.set('to_timestamp', toTimestamp);
      const res = await fetch(`${base}/api/v1/analytics/traceability?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to load traceability analytics');
      return res.json();
    },
    staleTime: 60_000,
  });

  if (loadingA || loadingG || loadingT) {
    return (
      <Box p={6} bg={bg} borderWidth={1} borderColor={border} borderRadius="lg">
        <Text>Loading analytics...</Text>
      </Box>
    );
  }

  if (errorA || errorG || errorT) {
    return (
      <Box p={6} bg={bg} borderWidth={1} borderColor={border} borderRadius="lg">
        <Alert status="error"><AlertIcon />Failed to load analytics</Alert>
      </Box>
    );
  }

  return (
    <Box p={6} bg={bg} borderWidth={1} borderColor={border} borderRadius="lg">
      <VStack spacing={6} align="stretch">
        <Text fontSize="xl" fontWeight="bold">Analytics</Text>

        {/* Activity */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>Activity</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel>Commits</StatLabel>
              <StatNumber>{activity?.commit_count ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>File Changes</StatLabel>
              <StatNumber>{activity?.file_changes ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Unique Authors</StatLabel>
              <StatNumber>{activity?.unique_authors ?? 0}</StatNumber>
            </Stat>
          </SimpleGrid>
        </Box>

        {/* Graph */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>Graph</Text>
          <SimpleGrid columns={{ base: 2, md: 6 }} spacing={4}>
            <Stat><StatLabel>Sprints</StatLabel><StatNumber>{graph?.nodes?.sprints ?? 0}</StatNumber></Stat>
            <Stat><StatLabel>Docs</StatLabel><StatNumber>{graph?.nodes?.documents ?? 0}</StatNumber></Stat>
            <Stat><StatLabel>Chunks</StatLabel><StatNumber>{graph?.nodes?.chunks ?? 0}</StatNumber></Stat>
            <Stat><StatLabel>Reqs</StatLabel><StatNumber>{graph?.nodes?.requirements ?? 0}</StatNumber></Stat>
            <Stat><StatLabel>Files</StatLabel><StatNumber>{graph?.nodes?.files ?? 0}</StatNumber></Stat>
            <Stat><StatLabel>Commits</StatLabel><StatNumber>{graph?.nodes?.commits ?? 0}</StatNumber></Stat>
          </SimpleGrid>
        </Box>

        {/* Traceability */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={2}>Traceability</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel>Total Requirements</StatLabel>
              <StatNumber>{trace?.total_requirements ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Implemented</StatLabel>
              <StatNumber>{trace?.implemented_requirements ?? 0}</StatNumber>
              <StatHelpText>{Math.round(((trace?.implemented_requirements ?? 0) / Math.max(trace?.total_requirements ?? 1, 1)) * 100)}%</StatHelpText>
            </Stat>
            <Stat>
              <StatLabel>Avg Files/Req</StatLabel>
              <StatNumber>{(trace?.avg_files_per_requirement ?? 0).toFixed(2)}</StatNumber>
            </Stat>
          </SimpleGrid>
        </Box>
      </VStack>
    </Box>
  );
}

export default RealAnalytics;