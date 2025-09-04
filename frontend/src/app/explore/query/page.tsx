'use client';

import { Box, Heading, VStack, Input, Text, SimpleGrid, Card, CardBody, Button, HStack, Badge } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchKnowledge } from '@/lib/api';

const templates = [
  'Show me the evolution of feature X',
  'Find all files that depend on component Y',
  'Analyze sprint velocity over time',
  'Identify deprecated patterns',
];

export default function QueryPage() {
  const [q, setQ] = useState('Find all requirements related to authentication');
  const { data } = useQuery({
    queryKey: ['knowledge-search', q],
    queryFn: () => searchKnowledge(q),
    enabled: q.length > 0,
  });

  return (
    <Box minH="100vh">
      <Header />
      <Box maxW="6xl" mx="auto" p={8}>
        <VStack align="start" spacing={6}>
          <Heading size="lg">Knowledge Query</Heading>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about the codebase" />
          <HStack wrap="wrap" gap={2}>
            {templates.map((t) => (
              <Button key={t} size="sm" onClick={() => setQ(t)} variant="outline">{t}</Button>
            ))}
          </HStack>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
            {data?.map((r) => (
              <Card key={r.id}>
                <CardBody>
                  <VStack align="start" spacing={1}>
                    <HStack>
                      <Badge>{r.type}</Badge>
                      <Text fontWeight="semibold">{r.title}</Text>
                    </HStack>
                    {r.snippet && <Text color="gray.500">{r.snippet}</Text>}
                  </VStack>
                </CardBody>
              </Card>
            )) || <Text color="gray.500">Type a query to start.</Text>}
          </SimpleGrid>
        </VStack>
      </Box>
    </Box>
  );
}

