'use client';

import React, { useState, useEffect } from 'react';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, Slider, SliderTrack, SliderFilledTrack, SliderThumb, HStack as ChakraHStack, Badge } from '@chakra-ui/react';
import ProgressiveStructureGraph from '../components/ProgressiveStructureGraph';

const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

interface Commit {
  hash: string;
  timestamp: string;
  message: string;
  author: string;
  files: FileChange[];
}

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  size: number;
  type: 'code' | 'document' | 'config' | 'other';
}

interface FileLifecycle {
  path: string;
  created_at: string;
  deleted_at?: string;
  modifications: number;
  current_size: number;
  type: 'code' | 'document' | 'config' | 'other';
  evolution_history: FileEvolution[];
}

interface FileEvolution {
  commit_hash: string;
  timestamp: string;
  action: 'created' | 'modified' | 'deleted';
  size: number;
  color: string;
}

export default function TimelinePage() {
  const [commits, setCommits] = useState<Commit[]>([]);
  const [fileLifecycles, setFileLifecycles] = useState<FileLifecycle[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [maxNodes, setMaxNodes] = useState(100);
  const [showFolderGroups, setShowFolderGroups] = useState(true);
  const [currentSubgraph, setCurrentSubgraph] = useState<{ nodes: any[]; edges: any[] } | null>(null);

  useEffect(() => {
    const fetchEvolutionData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/timeline?limit=50&max_files_per_commit=30`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch evolution timeline data');
        }

        const data = await response.json();
        
        console.log('TimelinePage: Fetched data', {
          commits: data.commits?.length || 0,
          fileLifecycles: data.file_lifecycles?.length || 0,
          sampleCommit: data.commits?.[0],
          sampleFileLifecycle: data.file_lifecycles?.[0]
        });
        
        setCommits(data.commits || []);
        setFileLifecycles(data.file_lifecycles || []);
        setCurrentTimeIndex(0); // Start from the first commit
        // Also hydrate subgraph for first commit
        if ((data.commits || []).length > 0) {
          const first = (data.commits || [])[0];
          try {
            const sg = await fetchCommitSubgraph(first.hash);
            setCurrentSubgraph(sg);
          } catch (e) {
            console.warn('Failed to fetch subgraph for initial commit, will use demo fallback.', e);
          }
        }
      } catch (err: any) {
        console.error("Error fetching evolution data:", err);
        setError(err.message || "Failed to load data");
        // Fallback to demo data if API fails
        const demoCommits = generateDemoCommits();
        const demoLifecycles = generateDemoFileLifecycles();
        setCommits(demoCommits);
        setFileLifecycles(demoLifecycles);
        // Try to fetch subgraph for first demo commit as well
        try {
          const sg = await fetchCommitSubgraph(demoCommits[0]?.hash);
          setCurrentSubgraph(sg);
        } catch {}
      } finally {
        setLoading(false);
      }
    };

    fetchEvolutionData();
  }, []);

  // Fetch subgraph scoped to a single commit
  const fetchCommitSubgraph = async (commitHash?: string) => {
    if (!commitHash) return { nodes: [], edges: [] };
    const params = new URLSearchParams();
    params.set('start_commit', commitHash);
    params.set('end_commit', commitHash);
    params.set('limit', '800');
    const url = `${DEV_GRAPH_API_URL}/api/v1/dev-graph/subgraph/by-commits?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch commit-scoped subgraph');
    const sg = await res.json();
    // Normalize keys to {nodes, edges}
    return { nodes: sg.nodes || [], edges: sg.edges || sg.links || [] };
  };

  // Update subgraph whenever current commit changes
  useEffect(() => {
    const run = async () => {
      const c = commits[currentTimeIndex];
      if (!c) return;
      try {
        const sg = await fetchCommitSubgraph(c.hash);
        setCurrentSubgraph(sg);
      } catch (e) {
        console.warn('Failed to fetch subgraph for commit', c.hash, e);
      }
    };
    run();
  }, [currentTimeIndex, commits]);


  const generateDemoCommits = (): Commit[] => [
    { 
      hash: 'abc123', 
      timestamp: '2025-01-01T10:00:00Z', 
      message: 'Initial commit',
      author: 'Developer',
      files: [
        { path: 'src/main.py', action: 'created', size: 1024, type: 'code' },
        { path: 'README.md', action: 'created', size: 512, type: 'document' }
      ]
    },
    { 
      hash: 'def456', 
      timestamp: '2025-01-02T10:00:00Z', 
      message: 'Add features',
      author: 'Developer',
      files: [
        { path: 'src/main.py', action: 'modified', size: 1536, type: 'code' },
        { path: 'src/utils.py', action: 'created', size: 768, type: 'code' }
      ]
    },
    { 
      hash: 'ghi789', 
      timestamp: '2025-01-03T10:00:00Z', 
      message: 'Fix bugs',
      author: 'Developer',
      files: [
        { path: 'src/main.py', action: 'modified', size: 1280, type: 'code' },
        { path: 'README.md', action: 'deleted', size: 0, type: 'document' }
      ]
    }
  ];

  const generateDemoFileLifecycles = (): FileLifecycle[] => [
    {
      path: 'src/main.py',
      created_at: '2025-01-01T10:00:00Z',
      modifications: 2,
      current_size: 1280,
      type: 'code',
      evolution_history: [
        { commit_hash: 'abc123', timestamp: '2025-01-01T10:00:00Z', action: 'created', size: 1024, color: '#3b82f6' },
        { commit_hash: 'def456', timestamp: '2025-01-02T10:00:00Z', action: 'modified', size: 1536, color: '#10b981' },
        { commit_hash: 'ghi789', timestamp: '2025-01-03T10:00:00Z', action: 'modified', size: 1280, color: '#10b981' }
      ]
    },
    {
      path: 'src/utils.py',
      created_at: '2025-01-02T10:00:00Z',
      modifications: 0,
      current_size: 768,
      type: 'code',
      evolution_history: [
        { commit_hash: 'def456', timestamp: '2025-01-02T10:00:00Z', action: 'created', size: 768, color: '#3b82f6' }
      ]
    },
    {
      path: 'README.md',
      created_at: '2025-01-01T10:00:00Z',
      deleted_at: '2025-01-03T10:00:00Z',
      modifications: 0,
      current_size: 0,
      type: 'document',
      evolution_history: [
        { commit_hash: 'abc123', timestamp: '2025-01-01T10:00:00Z', action: 'created', size: 512, color: '#3b82f6' },
        { commit_hash: 'ghi789', timestamp: '2025-01-03T10:00:00Z', action: 'deleted', size: 0, color: '#ef4444' }
      ]
    }
  ];

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleTimeChange = (index: number) => {
    setCurrentTimeIndex(index);
  };

  const handleNext = () => {
    if (currentTimeIndex < commits.length - 1) {
      setCurrentTimeIndex(currentTimeIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentTimeIndex > 0) {
      setCurrentTimeIndex(currentTimeIndex - 1);
    }
  };

  // Enhanced autoplay effect with variable speed
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying && commits.length > 0) {
      const speed = useBiologicalView ? 2000 : 1000; // Slower for biological view to appreciate evolution
      interval = setInterval(() => {
        setCurrentTimeIndex(prev => {
          const next = prev + 1;
          if (next >= commits.length) {
            setIsPlaying(false);
            return prev;
          }
          return next;
        });
      }, speed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, commits.length, useBiologicalView]);

  if (loading) {
    return (
      <Box p={8}>
        <VStack spacing={4}>
          <Spinner size="xl" />
          <Text>Loading evolution data...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={8}>
        <Alert status="error">
          <AlertIcon />
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={8}>
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="lg" mb={2}>Timeline Evolution</Heading>
          <Text color="gray.600">
            Watch your codebase evolve like a living organism. Each commit represents a generation, 
            files are organisms that grow, change, and die over time.
          </Text>
        </Box>

        {/* Playback Controls */}
        <HStack spacing={4} justify="center">
          <Button onClick={handlePrevious} isDisabled={currentTimeIndex === 0}>
            Previous
          </Button>
          <Button onClick={handlePlayPause} colorScheme="blue">
            {isPlaying ? 'Pause' : 'Play'}
          </Button>
          <Button onClick={handleNext} isDisabled={currentTimeIndex === commits.length - 1}>
            Next
          </Button>
        </HStack>

        {/* Current Commit Info */}
        {commits[currentTimeIndex] && (
          <Box p={4} bg="gray.50" borderRadius="md">
            <Text fontWeight="bold">
              Commit {currentTimeIndex + 1} of {commits.length}: {commits[currentTimeIndex].hash.substring(0, 8)}
            </Text>
            <Text fontSize="sm" color="gray.600">
              {commits[currentTimeIndex].message}
            </Text>
            <Text fontSize="xs" color="gray.500">
              {new Date(commits[currentTimeIndex].timestamp).toLocaleString()}
            </Text>
            <Text fontSize="xs" color="gray.500">
              Files: {commits[currentTimeIndex].files.length} | Author: {commits[currentTimeIndex].author}
            </Text>
          </Box>
        )}

        {/* Visualization Controls */}
        <Box p={4} bg="gray.50" borderRadius="md">
          <VStack spacing={4} align="stretch">
            <HStack justify="space-between" align="center">
              <Text fontSize="md" fontWeight="semibold">Visualization Controls</Text>
              <Badge colorScheme="blue" fontSize="sm">
                {commits.length > 0 ? `${commits[currentTimeIndex]?.files?.length || 0} files in current commit` : '0 files'}
              </Badge>
            </HStack>
            
            <HStack spacing={6} align="center">
              <VStack spacing={2} align="start">
                <Text fontSize="sm" fontWeight="medium">Max Nodes: {maxNodes}</Text>
                <Slider
                  value={maxNodes}
                  onChange={(value) => setMaxNodes(value)}
                  min={20}
                  max={500}
                  step={10}
                  width="200px"
                >
                  <SliderTrack>
                    <SliderFilledTrack />
                  </SliderTrack>
                  <SliderThumb />
                </Slider>
              </VStack>
              
              <VStack spacing={2} align="start">
                <Text fontSize="sm" fontWeight="medium">Group by Folders</Text>
                <Button
                  size="sm"
                  variant={showFolderGroups ? "solid" : "outline"}
                  colorScheme="green"
                  onClick={() => setShowFolderGroups(!showFolderGroups)}
                >
                  {showFolderGroups ? "Enabled" : "Disabled"}
                </Button>
              </VStack>
            </HStack>
          </VStack>
        </Box>

        {/* Main Visualization */}
        <ProgressiveStructureGraph
          commits={commits}
          currentTimeIndex={currentTimeIndex}
          width={1200}
          height={600}
          maxNodes={maxNodes}
          showFolderGroups={showFolderGroups}
        />
      </VStack>
    </Box>
  );
}
