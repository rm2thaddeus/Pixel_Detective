'use client';
import { Box, Heading, Spinner, Text, VStack, HStack, Button } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';

// Developer Graph API base URL (configurable via env)
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

export default function DevGraphPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [nodesRes, relationsRes, commitsRes] = await Promise.all([
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes/count`),
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations/count`),
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=5`)
        ]);

        const [nodes, relations, commits] = await Promise.all([
          nodesRes.json(),
          relationsRes.json(),
          commitsRes.json()
        ]);

        setStats({ nodes, relations, commits });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <Box minH="100vh">
        <Header />
        <VStack spacing={4} p={8}>
          <Spinner size="xl" color="blue.500" />
          <Text>Loading Dev Graph...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box minH="100vh">
      <Header />
      <VStack spacing={6} p={8} align="stretch" maxW="4xl" mx="auto">
        <Heading size="lg" color="blue.600">
          Developer Graph Dashboard - Simple View
        </Heading>
        
        {/* Simple Navigation */}
        <Box p={4} bg="gray.50" borderRadius="md">
          <Text fontSize="sm" fontWeight="medium" mb={2}>Navigate to other views:</Text>
          <HStack spacing={4}>
            <Text fontSize="sm" color="blue.600"><a href="/dev-graph/complex">Complex View</a></Text>
            <Text fontSize="sm">•</Text>
            <Text fontSize="sm" color="green.600"><a href="/dev-graph/enhanced">Enhanced Dashboard</a></Text>
            <Text fontSize="sm">•</Text>
            <Text fontSize="sm" color="purple.600" fontWeight="bold">Simple Dashboard (Current)</Text>
          </HStack>
        </Box>
        
        {stats && (
          <VStack spacing={4} align="stretch">
            <Box p={6} borderWidth={1} borderRadius="lg" shadow="sm">
              <Heading size="md" mb={4}>Graph Statistics</Heading>
              <Text><strong>Total Nodes:</strong> {stats.nodes.total}</Text>
              <Text><strong>Total Relations:</strong> {stats.relations.total}</Text>
              <Text><strong>Recent Commits:</strong> {stats.commits.length}</Text>
            </Box>

            {stats.commits.length > 0 && (
              <Box p={6} borderWidth={1} borderRadius="lg" shadow="sm">
                <Heading size="md" mb={4}>Recent Commits</Heading>
                <VStack align="stretch" spacing={2}>
                  {stats.commits.slice(0, 3).map((commit: any, index: number) => (
                    <Box key={commit.hash} p={3} bg="gray.50" borderRadius="md">
                      <Text fontSize="sm" fontWeight="bold">{commit.message}</Text>
                      <Text fontSize="xs" color="gray.600">
                        {commit.author_name} • {new Date(commit.timestamp).toLocaleDateString()}
                      </Text>
                    </Box>
                  ))}
                </VStack>
              </Box>
            )}

            <Box p={6} borderWidth={1} borderRadius="lg" shadow="sm">
              <Heading size="md" mb={4}>Available Features</Heading>
              <VStack align="stretch" spacing={2}>
                <Text>• Neo4j Graph Database with {stats.nodes.total} nodes</Text>
                <Text>• Temporal relationships tracking</Text>
                <Text>• Sprint-based documentation mapping</Text>
                <Text>• Git commit history integration</Text>
              </VStack>
            </Box>

            <Button
              colorScheme="blue"
              size="lg"
              onClick={() => window.open(`${DEV_GRAPH_API_URL}/docs`, '_blank')}
            >
              View API Documentation
            </Button>
          </VStack>
        )}
      </VStack>
    </Box>
  );
}
