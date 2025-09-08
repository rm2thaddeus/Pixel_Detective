'use client';

import React, { useState, useEffect } from 'react';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, Tabs, TabList, TabPanels, Tab, TabPanel, Switch, FormLabel } from '@chakra-ui/react';
import TemporalEvolutionGraph from '../components/TemporalEvolutionGraph';
import BiologicalEvolutionGraph from '../components/BiologicalEvolutionGraph';
import SimplePhysicsSimulation from '../components/SimplePhysicsSimulation';

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
  const [useBiologicalView, setUseBiologicalView] = useState(true);
  const [viewMode, setViewMode] = useState<'biological' | 'technical' | 'physics'>('physics');
  const [evolutionSnapshots, setEvolutionSnapshots] = useState<any[]>([]);

  useEffect(() => {
    const fetchEvolutionData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/timeline?limit=50`);
        
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
        
        // Generate evolution snapshots for biological view
        const snapshots = generateEvolutionSnapshots(data.commits || [], data.file_lifecycles || []);
        setEvolutionSnapshots(snapshots);
      } catch (err: any) {
        console.error("Error fetching evolution data:", err);
        setError(err.message || "Failed to load data");
        // Fallback to demo data if API fails
        const demoCommits = generateDemoCommits();
        const demoLifecycles = generateDemoFileLifecycles();
        setCommits(demoCommits);
        setFileLifecycles(demoLifecycles);
        
        // Generate demo evolution snapshots
        const demoSnapshots = generateEvolutionSnapshots(demoCommits, demoLifecycles);
        setEvolutionSnapshots(demoSnapshots);
      } finally {
        setLoading(false);
      }
    };

    fetchEvolutionData();
  }, []);

  const generateEvolutionSnapshots = (commits: Commit[], lifecycles: FileLifecycle[]): any[] => {
    return commits.map((commit, index) => {
      // Get files visible at this commit
      const visibleFiles = lifecycles.filter(file => {
        const createdBefore = new Date(file.created_at) <= new Date(commit.timestamp);
        const notDeletedYet = !file.deleted_at || new Date(file.deleted_at) > new Date(commit.timestamp);
        return createdBefore && notDeletedYet;
      }).map(file => {
        // Determine file status at this commit
        let status = 'alive';
        const fileInCommit = commit.files.find(f => f.path === file.path);
        if (fileInCommit) {
          if (fileInCommit.action === 'deleted') status = 'deleted';
          else if (fileInCommit.action === 'modified') status = 'modified';
        }
        
        return {
          id: file.path,
          path: file.path,
          type: file.type,
          created_at: file.created_at,
          deleted_at: file.deleted_at,
          last_modified: commit.timestamp,
          size: fileInCommit?.size || file.current_size,
          commit_count: file.modifications,
          status,
          modifications: file.modifications
        };
      });

      return {
        timestamp: commit.timestamp,
        commit_hash: commit.hash,
        files: visibleFiles,
        branches: ['main'], // Simplified for demo
        active_developers: [commit.author],
        commit: {
          hash: commit.hash,
          message: commit.message,
          timestamp: commit.timestamp,
          author_name: commit.author,
          files_changed: commit.files.map(f => f.path),
          x: 0,
          y: 0
        }
      };
    });
  };

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

        {/* View Toggle */}
        <HStack spacing={4} justify="center" py={4}>
          <FormLabel htmlFor="view-toggle" mb={0}>
            Visualization Mode:
          </FormLabel>
          <Switch
            id="view-toggle"
            isChecked={useBiologicalView}
            onChange={(e) => setUseBiologicalView(e.target.checked)}
            colorScheme="purple"
          />
          <Text fontSize="sm" color={useBiologicalView ? 'purple.600' : 'gray.600'}>
            {useBiologicalView ? '🧬 Biological Evolution' : '📊 Technical Timeline'}
          </Text>
        </HStack>

        {/* Evolution Visualization */}
        <Tabs variant="enclosed" colorScheme="purple" index={viewMode === 'biological' ? 0 : viewMode === 'technical' ? 1 : 2} onChange={(index) => setViewMode(index === 0 ? 'biological' : index === 1 ? 'technical' : 'physics')}>
          <TabList>
            <Tab>Evolution View</Tab>
            <Tab>Technical Details</Tab>
            <Tab>Physics Simulation</Tab>
          </TabList>
          <TabPanels>
            <TabPanel>
              {useBiologicalView && evolutionSnapshots.length > 0 ? (
                <BiologicalEvolutionGraph
                  snapshot={evolutionSnapshots[currentTimeIndex]}
                  previousSnapshot={currentTimeIndex > 0 ? evolutionSnapshots[currentTimeIndex - 1] : undefined}
                  height={900}
                  width={1200}
                  showLabels={true}
                  enableAnimation={true}
                  isPlaying={isPlaying}
                  currentIndex={currentTimeIndex}
                  totalSnapshots={evolutionSnapshots.length}
                  onPlayPause={handlePlayPause}
                  onNext={handleNext}
                  onPrevious={handlePrevious}
                />
              ) : (
                <TemporalEvolutionGraph
                  commits={commits}
                  fileLifecycles={fileLifecycles}
                  currentTimeIndex={currentTimeIndex}
                  isPlaying={isPlaying}
                  onTimeChange={handleTimeChange}
                  width={1200}
                  height={600}
                />
              )}
            </TabPanel>
            <TabPanel>
              <TemporalEvolutionGraph
                commits={commits}
                fileLifecycles={fileLifecycles}
                currentTimeIndex={currentTimeIndex}
                isPlaying={isPlaying}
                onTimeChange={handleTimeChange}
                width={1200}
                height={600}
              />
            </TabPanel>
            <TabPanel>
              <SimplePhysicsSimulation
                commits={commits.map(commit => ({
                  id: commit.hash,
                  message: commit.message,
                  timestamp: commit.timestamp,
                  files: commit.files.map(file => ({
                    id: file.path,
                    path: file.path,
                    type: file.type === 'document' ? 'doc' : file.type === 'config' ? 'config' : file.type === 'other' ? 'test' : 'code',
                    status: file.action === 'created' ? 'new' : file.action === 'deleted' ? 'deleted' : 'modified',
                    modifications: 1,
                    commit_count: 1,
                    created_at: commit.timestamp,
                    last_modified: commit.timestamp
                  }))
                }))}
                currentIndex={currentTimeIndex}
                height={700}
                width={1200}
                isPlaying={isPlaying}
                onTimeChange={setCurrentTimeIndex}
              />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}