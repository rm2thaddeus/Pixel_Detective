'use client';

import { Box, Heading, VStack, SimpleGrid, Card, CardBody, Text, Badge } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useQuery } from '@tanstack/react-query';
import { generateArchitectureInsights } from '@/lib/api';

export default function AnalysisPage() {
  const { data } = useQuery({ queryKey: ['architecture-insights'], queryFn: generateArchitectureInsights });

  return (
    <Box minH="100vh">
      <Header />
      <Box maxW="6xl" mx="auto" p={8}>
        <VStack align="start" spacing={6} w="full">
          <Heading size="lg">Architecture Analysis</Heading>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
            <Card>
              <CardBody>
                <Heading size="sm" mb={2}>Dependencies</Heading>
                <VStack align="start" spacing={1}>
                  {data?.dependencies?.map((d, idx) => (
                    <Text key={idx}>{d.source} ➜ {d.target} {d.weight ? `(${d.weight})` : ''}</Text>
                  )) || <Text color="gray.500">No data</Text>}
                </VStack>
              </CardBody>
            </Card>
            <Card>
              <CardBody>
                <Heading size="sm" mb={2}>Bottlenecks</Heading>
                <VStack align="start" spacing={1}>
                  {data?.bottlenecks?.map((b) => (
                    <Text key={b.id}><Badge mr={2}>{b.metric}</Badge>{b.label}: {b.value}</Text>
                  )) || <Text color="gray.500">No data</Text>}
                </VStack>
              </CardBody>
            </Card>
          </SimpleGrid>
        </VStack>
      </Box>
    </Box>
  );
}

