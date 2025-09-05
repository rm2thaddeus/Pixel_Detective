'use client';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, useColorModeValue, Badge, Icon, Flex, Divider, Grid, GridItem } from '@chakra-ui/react';
import { useState, useEffect, useMemo } from 'react';
import { Header } from '@/components/Header';
import { Link as ChakraLink } from '@chakra-ui/react';
import { FaArrowLeft, FaPlay, FaPause, FaStepForward, FaStepBackward, FaTree, FaLeaf, FaSeedling, FaTrash } from 'react-icons/fa';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues
const BiologicalEvolutionGraph = dynamic(() => import('../components/BiologicalEvolutionGraph'), { ssr: false });

// Developer Graph API base URL
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

interface Commit {
  hash: string;
  message: string;
  timestamp: string;
  author_name: string;
  author_email: string;
  files_changed: string[];
}

interface FileNode {
  id: string;
  path: string;
  type: 'code' | 'doc' | 'config' | 'test';
  created_at: string;
  deleted_at?: string;
  last_modified: string;
  size: number;
  commit_count: number;
  status: 'alive' | 'deleted' | 'modified';
}

interface EvolutionSnapshot {
  timestamp: string;
  commit_hash: string;
  files: FileNode[];
  branches: string[];
  active_developers: string[];
}

export default function TimelineEvolutionPage() {
  const [commits, setCommits] = useState<Commit[]>([]);
  const [evolutionSnapshots, setEvolutionSnapshots] = useState<EvolutionSnapshot[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const pageBgColor = useColorModeValue('gray.50', 'gray.900');

  useEffect(() => {
    const fetchEvolutionData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch commits and create evolution snapshots with graceful error handling
        const commitsRes = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=100`).catch(() => null);
        
        if (!commitsRes || !commitsRes.ok) {
          // Create demo data when API is not available
          const demoCommits: Commit[] = [
            {
              hash: 'demo-001',
              message: 'Initial commit - project setup',
              timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
              author_name: 'Developer',
              author_email: 'dev@example.com',
              files_changed: ['README.md', 'package.json', 'src/index.js']
            },
            {
              hash: 'demo-002',
              message: 'Add core functionality',
              timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
              author_name: 'Developer',
              author_email: 'dev@example.com',
              files_changed: ['src/core.js', 'src/utils.js', 'tests/core.test.js']
            },
            {
              hash: 'demo-003',
              message: 'Implement features',
              timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
              author_name: 'Developer',
              author_email: 'dev@example.com',
              files_changed: ['src/features.js', 'docs/features.md', 'config/settings.json']
            }
          ];
          setCommits(demoCommits);
          setError('API not available - showing demo data');
        } else {
          const commitsData: Commit[] = await commitsRes.json();
          setCommits(commitsData);
        }

        // Create evolution snapshots from current commits
        const currentCommits = commits.length > 0 ? commits : [
          {
            hash: 'demo-001',
            message: 'Initial commit - project setup',
            timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            author_name: 'Developer',
            author_email: 'dev@example.com',
            files_changed: ['README.md', 'package.json', 'src/index.js']
          }
        ];

        const snapshots: EvolutionSnapshot[] = currentCommits.map((commit, index) => ({
          timestamp: commit.timestamp,
          commit_hash: commit.hash,
          files: commit.files_changed.map((filePath, fileIndex) => ({
            id: `${commit.hash}-${fileIndex}`,
            path: filePath,
            type: getFileType(filePath),
            created_at: commit.timestamp,
            last_modified: commit.timestamp,
            size: Math.random() * 1000 + 100, // Mock size
            commit_count: Math.floor(Math.random() * 10) + 1,
            status: 'alive' as const
          })),
          branches: ['main', 'develop'], // Mock branches
          active_developers: [commit.author_name]
        }));

        setEvolutionSnapshots(snapshots);
      } catch (err) {
        console.error('Failed to fetch evolution data:', err);
        setError('Failed to load evolution data');
      } finally {
        setLoading(false);
      }
    };

    fetchEvolutionData();
  }, []);

  const getFileType = (path: string): 'code' | 'doc' | 'config' | 'test' => {
    if (path.includes('.md') || path.includes('docs/')) return 'doc';
    if (path.includes('test/') || path.includes('.test.') || path.includes('.spec.')) return 'test';
    if (path.includes('config') || path.includes('.json') || path.includes('.yaml')) return 'config';
    return 'code';
  };

  // Playback controls
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTimeIndex(prev => {
        const next = prev + 1;
        if (next >= evolutionSnapshots.length) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, evolutionSnapshots.length]);

  const currentSnapshot = evolutionSnapshots[currentTimeIndex];
  const progress = evolutionSnapshots.length > 0 ? (currentTimeIndex / (evolutionSnapshots.length - 1)) * 100 : 0;

  if (loading) {
    return (
      <Box minH="100vh" bg={pageBgColor}>
        <Header />
        <VStack spacing={4} p={8} align="center" justify="center" minH="60vh">
          <Spinner size="xl" color="blue.500" />
          <Text>Loading Evolution Timeline...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box minH="100vh" bg={pageBgColor}>
        <Header />
        <VStack spacing={4} p={8} align="center" justify="center" minH="60vh">
          <Alert status="error" maxW="md">
            <AlertIcon />
            {error}
          </Alert>
        </VStack>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg={pageBgColor}>
      <Header />
      <VStack spacing={6} p={8} align="stretch" maxW="7xl" mx="auto">
        {/* Header */}
        <Flex justify="space-between" align="center">
          <HStack>
            <Button as={ChakraLink} href="/dev-graph/welcome" variant="ghost" size="sm">
              <Icon as={FaArrowLeft} mr={2} />
              Back to Dashboard
            </Button>
            <Divider orientation="vertical" height="20px" />
            <Heading size="lg" color="blue.600">
              Timeline Evolution
            </Heading>
          </HStack>
          <HStack spacing={2}>
            <Button as={ChakraLink} href="/dev-graph/structure" variant="outline" size="sm">
              Switch to Structure View
            </Button>
          </HStack>
        </Flex>

        {/* Biological Metaphor Explanation */}
        <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
          <HStack mb={3}>
            <Icon as={FaTree} color="green.500" />
            <Heading size="md">Biological Evolution Metaphor</Heading>
          </HStack>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Your codebase evolves like a living ecosystem. Each commit represents a generation, 
            files are organisms that live and die, and branches are evolutionary lineages.
          </Text>
          {error && (
            <Alert status="warning" size="sm" mb={3}>
              <AlertIcon />
              <Text fontSize="xs">
                {error} - Some features may be limited without API connection.
              </Text>
            </Alert>
          )}
          <HStack spacing={6} wrap="wrap">
            <HStack>
              <Icon as={FaSeedling} color="green.500" />
              <Text fontSize="xs"><strong>Green:</strong> New files (born)</Text>
            </HStack>
            <HStack>
              <Icon as={FaLeaf} color="blue.500" />
              <Text fontSize="xs"><strong>Blue:</strong> Modified files (evolved)</Text>
            </HStack>
            <HStack>
              <Icon as={FaTrash} color="red.500" />
              <Text fontSize="xs"><strong>Red:</strong> Deleted files (extinct)</Text>
            </HStack>
          </HStack>
        </Box>

        {/* Timeline Controls */}
        <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
          <VStack spacing={4}>
            <HStack spacing={4} w="full">
              <Button
                size="sm"
                onClick={() => setCurrentTimeIndex(Math.max(0, currentTimeIndex - 1))}
                isDisabled={currentTimeIndex === 0}
              >
                <Icon as={FaStepBackward} />
              </Button>
              
              <Button
                size="sm"
                colorScheme={isPlaying ? "red" : "green"}
                onClick={() => setIsPlaying(!isPlaying)}
              >
                <Icon as={isPlaying ? FaPause : FaPlay} />
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              
              <Button
                size="sm"
                onClick={() => setCurrentTimeIndex(Math.min(evolutionSnapshots.length - 1, currentTimeIndex + 1))}
                isDisabled={currentTimeIndex >= evolutionSnapshots.length - 1}
              >
                <Icon as={FaStepForward} />
              </Button>

              <Divider orientation="vertical" height="20px" />

              <Text fontSize="sm" color="gray.600">
                Speed:
              </Text>
              <HStack spacing={1}>
                {[0.5, 1, 2, 4].map(speed => (
                  <Button
                    key={speed}
                    size="xs"
                    variant={playbackSpeed === speed ? "solid" : "outline"}
                    onClick={() => setPlaybackSpeed(speed)}
                  >
                    {speed}x
                  </Button>
                ))}
              </HStack>
            </HStack>

            {/* Progress Bar */}
            <Box w="full">
              <HStack justify="space-between" mb={1}>
                <Text fontSize="xs" color="gray.600">
                  Generation {currentTimeIndex + 1} of {evolutionSnapshots.length}
                </Text>
                <Text fontSize="xs" color="gray.600">
                  {progress.toFixed(1)}%
                </Text>
              </HStack>
              <Box
                w="full"
                h="8px"
                bg="gray.200"
                borderRadius="md"
                overflow="hidden"
              >
                <Box
                  h="100%"
                  bg="linear-gradient(to right, #48bb78, #38a169)"
                  width={`${progress}%`}
                  transition="width 0.3s ease"
                />
              </Box>
            </Box>
          </VStack>
        </Box>

        {/* Current Generation Info */}
        {currentSnapshot && (
          <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
            <HStack justify="space-between" mb={3}>
              <Heading size="md">Generation {currentTimeIndex + 1}</Heading>
              <Badge colorScheme="blue">
                {new Date(currentSnapshot.timestamp).toLocaleDateString()}
              </Badge>
            </HStack>
            
            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={4}>
              <Box>
                <Text fontSize="sm" fontWeight="bold" color="gray.600">Commit</Text>
                <Text fontSize="sm" fontFamily="mono" color="blue.600">
                  {currentSnapshot.commit_hash.substring(0, 8)}...
                </Text>
              </Box>
              
              <Box>
                <Text fontSize="sm" fontWeight="bold" color="gray.600">Files in Generation</Text>
                <Text fontSize="sm" color="green.600">
                  {currentSnapshot.files.length} organisms
                </Text>
              </Box>
              
              <Box>
                <Text fontSize="sm" fontWeight="bold" color="gray.600">Active Branches</Text>
                <Text fontSize="sm" color="purple.600">
                  {currentSnapshot.branches.length} lineages
                </Text>
              </Box>
            </Grid>
          </Box>
        )}

        {/* Evolution Graph */}
        <Box h="600px" bg={bgColor} borderRadius="md" borderColor={borderColor} p={4}>
          {currentSnapshot ? (
            <BiologicalEvolutionGraph
              snapshot={currentSnapshot}
              height={560}
              showLabels={true}
              enableAnimation={isPlaying}
            />
          ) : (
            <VStack align="center" justify="center" h="full">
              <Spinner size="lg" color="blue.500" />
              <Text>Loading evolution snapshot...</Text>
            </VStack>
          )}
        </Box>

        {/* File Type Breakdown */}
        {currentSnapshot && (
          <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
            <Heading size="md" mb={3}>Ecosystem Composition</Heading>
            <HStack spacing={6} wrap="wrap">
              {['code', 'doc', 'config', 'test'].map(type => {
                const count = currentSnapshot.files.filter(f => f.type === type).length;
                const color = type === 'code' ? 'blue' : type === 'doc' ? 'green' : type === 'config' ? 'orange' : 'purple';
                return (
                  <HStack key={type}>
                    <Box w={3} h={3} bg={`${color}.500`} borderRadius="full" />
                    <Text fontSize="sm" textTransform="capitalize">{type}</Text>
                    <Badge colorScheme={color}>{count}</Badge>
                  </HStack>
                );
              })}
            </HStack>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
