'use client';

import { Box, Heading, Text, SimpleGrid, Card, CardBody, Button, VStack } from '@chakra-ui/react';
import { useRouter } from 'next/navigation';
import { Header } from '@/components/Header';

export default function ExploreIndexPage() {
  const router = useRouter();
  const items = [
    { title: 'Timeline', desc: 'Time-travel through feature evolution', path: '/explore/timeline' },
    { title: 'Graph', desc: 'Interactive knowledge graph exploration', path: '/explore/graph' },
    { title: 'Analysis', desc: 'Architecture, dependencies and bottlenecks', path: '/explore/analysis' },
    { title: 'Query', desc: 'Ask questions and build queries', path: '/explore/query' },
  ];

  return (
    <Box minH="100vh">
      <Header />
      <Box maxW="6xl" mx="auto" p={8}>
        <VStack align="start" spacing={6}>
          <Heading size="lg">Knowledge Graph Exploration</Heading>
          <Text color="gray.500">Pick a view to start exploring the codebase evolution and relationships.</Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} w="full">
            {items.map((it) => (
              <Card key={it.title}>
                <CardBody>
                  <VStack align="start" spacing={3}>
                    <Heading size="md">{it.title}</Heading>
                    <Text color="gray.500">{it.desc}</Text>
                    <Button onClick={() => router.push(it.path)} colorScheme="blue" alignSelf="flex-start">
                      Open {it.title}
                    </Button>
                  </VStack>
                </CardBody>
              </Card>
            ))}
          </SimpleGrid>
        </VStack>
      </Box>
    </Box>
  );
}

