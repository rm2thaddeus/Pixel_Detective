'use client';

import React, { useState, useEffect } from 'react';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, Slider, SliderTrack, SliderFilledTrack, SliderThumb, HStack as ChakraHStack, Badge, useColorModeValue, RangeSlider, RangeSliderTrack, RangeSliderFilledTrack, RangeSliderThumb } from '@chakra-ui/react';
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
  lines_after?: number;
  loc?: number;
  additions?: number;
  deletions?: number;
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
  console.log('TimelinePage: Component rendering');
  const [commits, setCommits] = useState<Commit[]>([]);
  const [fileLifecycles, setFileLifecycles] = useState<FileLifecycle[]>([]);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [maxNodes, setMaxNodes] = useState(100);
  const [useAutoNodeBudget, setUseAutoNodeBudget] = useState(true);
  const [autoNodeBudget, setAutoNodeBudget] = useState(200);
  const [showFolderGroups, setShowFolderGroups] = useState(true);
  const [focusedView, setFocusedView] = useState(true);
  const [currentSubgraph, setCurrentSubgraph] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [range, setRange] = useState<[number, number]>([0, 0]);
  const [totalCommits, setTotalCommits] = useState(0);
  const [sizeByLOC, setSizeByLOC] = useState(true);
  const [colorMode, setColorMode] = useState<'folder' | 'type' | 'commit-flow' | 'activity' | 'none'>('folder');
  const [highlightDocs, setHighlightDocs] = useState(true);
  const [edgeEmphasis, setEdgeEmphasis] = useState(0.4);
  const [enableZoom, setEnableZoom] = useState(true);
  const [resetToken, setResetToken] = useState(0);
  // Compute adaptive node budget based on device/browser capabilities and viewport
  useEffect(() => {
    const computeAdaptiveMaxNodes = () => {
      const mem = (navigator as any).deviceMemory || 4; // in GB
      const cores = navigator.hardwareConcurrency || 4;
      const area = Math.max(1, (window.innerWidth || 1200) * (window.innerHeight || 800));
      const areaFactor = Math.min(2, Math.sqrt(area) / 1000); // ~0.8–2.0
      // Base derived from mem and cores
      const base = 250 * (mem / 4) * (cores / 4) * areaFactor;
      // Clamp to safe range
      const budget = Math.max(100, Math.min(2000, Math.floor(base)));
      return budget;
    };

    const recalc = () => {
      const budget = computeAdaptiveMaxNodes();
      setAutoNodeBudget(budget);
      if (useAutoNodeBudget) {
        setMaxNodes(budget);
      }
    };

    recalc();
    window.addEventListener('resize', recalc);
    return () => window.removeEventListener('resize', recalc);
  }, [useAutoNodeBudget]);


  // Dark mode color values
  const bgColor = useColorModeValue('white', 'gray.800');
  const cardBgColor = useColorModeValue('gray.50', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'gray.200');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');

  console.log('TimelinePage: About to run useEffect');
  useEffect(() => {
    console.log('TimelinePage: useEffect triggered, starting data fetch');
    console.log('TimelinePage: useEffect is running!');
    const fetchEvolutionData = async () => {
      try {
        console.log('TimelinePage: Starting data fetch, API URL:', DEV_GRAPH_API_URL);
        setLoading(true);
        setError(null);

        // Load commits with expanded backend limit so the UI can span the full range
        const filesPerCommit = 50; // Keep file payload per commit bounded for perf
        // Request a large upper bound; backend now allows up to 5000
        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/timeline?limit=5000&max_files_per_commit=${filesPerCommit}`);
        
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
        
        // Debug LOC data specifically
        if (data.commits?.[0]?.files) {
          const filesWithLoc = data.commits[0].files.filter(f => f.loc > 0 || f.lines_after > 0);
          console.log('TimelinePage: Files with LOC data', {
            totalFiles: data.commits[0].files.length,
            filesWithLoc: filesWithLoc.length,
            sampleFilesWithLoc: filesWithLoc.slice(0, 3)
          });
        }
        
        setCommits(data.commits || []);
        setFileLifecycles(data.file_lifecycles || []);
        setTotalCommits(data.total_commits || (data.commits || []).length);
        setCurrentTimeIndex(0); // Start from the first commit
        if ((data.commits || []).length > 0) {
          setRange([0, (data.commits || []).length - 1]); // Allow full commit range
        }
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

  const handleResetToRangeStart = () => {
    console.log('Reset button clicked', {
      currentRange: range,
      currentIndex: currentTimeIndex,
      settingTo: range[0],
      totalCommits,
      firstCommit: commits[0]?.hash?.substring(0, 8),
      firstCommitMessage: commits[0]?.message?.substring(0, 50)
    });
    setCurrentTimeIndex(range[0]);
    setIsPlaying(false);
    // force ProgressiveStructureGraph to reset zoom/sim
    setResetToken((t) => t + 1);
    // Force a small delay to ensure state updates
    setTimeout(() => {
      console.log('After reset - currentTimeIndex should be:', range[0], 'actual:', currentTimeIndex);
    }, 100);
  };

  const handleTimeChange = (index: number) => {
    setCurrentTimeIndex(index);
  };

  const handleNext = () => {
    if (currentTimeIndex < range[1]) {
      setCurrentTimeIndex(currentTimeIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentTimeIndex > range[0]) {
      setCurrentTimeIndex(currentTimeIndex - 1);
    }
  };

  // Enhanced autoplay effect with consistent speed - respects commit range
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying && commits.length > 0 && range[1] > range[0]) {
      const speed = 1500; // Consistent speed for smooth playback
      interval = setInterval(() => {
        setCurrentTimeIndex(prev => {
          const next = prev + 1;
          if (next > range[1]) {
            setIsPlaying(false);
            return prev;
          }
          return next;
        });
      }, speed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, commits.length, range]);

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
    <Box p={8} bg={bgColor} minH="100vh">
      <VStack spacing={6} align="stretch">
        <Box>
          <Heading size="lg" mb={2} color={textColor}>Timeline Evolution</Heading>
          <Text color={mutedTextColor}>
            Watch your codebase evolve like a living organism. Each commit represents a generation, 
            files are organisms that grow, change, and die over time.
          </Text>
        </Box>

        {/* Playback Controls */}
        <HStack spacing={4} justify="center">
          <Button 
            onClick={(e) => {
              e.preventDefault();
              console.log('Button clicked!', e);
              handleResetToRangeStart();
            }}
            colorScheme="gray" 
            size="sm"
            isDisabled={commits.length === 0}
          >
            Reset to Range Start
          </Button>
          <Button onClick={handlePrevious} isDisabled={currentTimeIndex <= range[0]} colorScheme="purple">
            Previous
          </Button>
          <Button onClick={handlePlayPause} colorScheme="blue">
            {isPlaying ? 'Pause' : 'Play'}
          </Button>
          <Button onClick={handleNext} isDisabled={currentTimeIndex >= range[1]} colorScheme="purple">
            Next
          </Button>
        </HStack>
        
        {/* Range Info */}
        <Text fontSize="sm" color={mutedTextColor} textAlign="center">
          Playing within range: {range[0] + 1} – {range[1] + 1} of {totalCommits} total | Current: {currentTimeIndex + 1}
          {currentTimeIndex === range[0] && <Text as="span" color="green.400" fontWeight="bold"> (At range start)</Text>}
        </Text>

        {/* Current Commit Info */}
        {commits[currentTimeIndex] && (
          <Box p={4} bg={cardBgColor} borderRadius="md" border="1px solid" borderColor={borderColor}>
            <Text fontWeight="bold" color={textColor}>
              Commit {currentTimeIndex + 1} of {totalCommits} (Range: {range[0] + 1}–{range[1] + 1}): {commits[currentTimeIndex].hash.substring(0, 8)}
            </Text>
            <Text fontSize="sm" color={mutedTextColor}>
              {commits[currentTimeIndex].message}
            </Text>
            <Text fontSize="xs" color={mutedTextColor}>
              {new Date(commits[currentTimeIndex].timestamp).toLocaleString()}
            </Text>
            <Text fontSize="xs" color={mutedTextColor}>
              Files: {commits[currentTimeIndex].files.length} | Author: {commits[currentTimeIndex].author}
            </Text>
          </Box>
        )}

        {/* Visualization Controls */}
        <Box p={4} bg={cardBgColor} borderRadius="md" border="1px solid" borderColor={borderColor}>
          <VStack spacing={4} align="stretch">
            <HStack justify="space-between" align="center">
              <Text fontSize="md" fontWeight="semibold" color={textColor}>Visualization Controls</Text>
              <Badge colorScheme="blue" fontSize="sm">
                {commits.length > 0 ? `${commits[currentTimeIndex]?.files?.length || 0} files in current commit` : '0 files'}
              </Badge>
            </HStack>
            
            <HStack spacing={6} align="center">
              <VStack spacing={2} align="start">
                <HStack spacing={3}>
                  <Text fontSize="sm" fontWeight="medium" color={textColor}>Max Nodes: {useAutoNodeBudget ? autoNodeBudget : maxNodes}</Text>
                  <Button size="sm" variant={useAutoNodeBudget ? 'solid' : 'outline'} colorScheme="blue" onClick={() => {
                    const next = !useAutoNodeBudget;
                    setUseAutoNodeBudget(next);
                    if (next) setMaxNodes(autoNodeBudget);
                  }}>
                    Auto {useAutoNodeBudget ? 'On' : 'Off'}
                  </Button>
                </HStack>
                <Slider
                  value={useAutoNodeBudget ? autoNodeBudget : maxNodes}
                  onChange={(value) => { setMaxNodes(value); setUseAutoNodeBudget(false); }}
                  min={50}
                  max={2000}
                  step={10}
                  width="240px"
                >
                  <SliderTrack bg={borderColor}>
                    <SliderFilledTrack bg="blue.500" />
                  </SliderTrack>
                  <SliderThumb bg="blue.500" />
                </Slider>
              </VStack>
            </HStack>

            {/* Commit Range */}
            <VStack spacing={2} align="start">
              <Text fontSize="sm" fontWeight="medium" color={textColor}>Commit Range</Text>
              <RangeSlider
                value={range}
                min={0}
                max={Math.max(0, totalCommits - 1)}
                step={1}
                isDisabled={commits.length === 0}
                onChange={(val: [number, number]) => {
                  setRange(val);
                  // Keep currentTimeIndex within the new range
                  if (currentTimeIndex < val[0]) setCurrentTimeIndex(val[0]);
                  if (currentTimeIndex > val[1]) setCurrentTimeIndex(val[1]);
                }}
                width="300px"
              >
                <RangeSliderTrack bg={borderColor}>
                  <RangeSliderFilledTrack bg="purple.500" />
                </RangeSliderTrack>
                <RangeSliderThumb index={0} bg="purple.400" />
                <RangeSliderThumb index={1} bg="purple.400" />
              </RangeSlider>
              <Text fontSize="xs" color={mutedTextColor}>
                Showing commits {range[0] + 1} – {range[1] + 1} of {totalCommits} total
              </Text>
            </VStack>

            {/* Encodings & Interactions */}
            <VStack align="stretch" spacing={3}>
              {/*
              <Button size="sm" variant={sizeByLOC ? 'solid' : 'outline'} colorScheme="orange" onClick={() => setSizeByLOC(!sizeByLOC)}>
                📏 Size by LOC {sizeByLOC ? 'On' : 'Off'}
              </Button>
              <Button size="sm" variant={colorByLOC ? 'solid' : 'outline'} colorScheme="pink" onClick={() => setColorByLOC(!colorByLOC)}>
                🎨 Color by LOC {colorByLOC ? 'On' : 'Off'}
              </Button>
              <Button size="sm" variant={showFolderGroups ? 'solid' : 'outline'} colorScheme="green" onClick={() => setShowFolderGroups(!showFolderGroups)}>
                📁 Folders {showFolderGroups ? 'On' : 'Off'}
              </Button>
              <Button size="sm" variant={focusedView ? 'solid' : 'outline'} colorScheme="blue" onClick={() => setFocusedView(!focusedView)}>
                🔍 Focus {focusedView ? 'On' : 'Off'}
              </Button>
              <Button size="sm" variant={enableZoom ? 'solid' : 'outline'} colorScheme="teal" onClick={() => setEnableZoom(!enableZoom)}>
                🔍 Zoom {enableZoom ? 'On' : 'Off'}
              </Button>
              */}
              <HStack spacing={3} wrap="wrap">
                <Button size="sm" variant={sizeByLOC ? 'solid' : 'outline'} colorScheme="orange" onClick={() => setSizeByLOC(!sizeByLOC)}>
                  Size by LOC {sizeByLOC ? 'On' : 'Off'}
                </Button>
                <Button size="sm" variant={showFolderGroups ? 'solid' : 'outline'} colorScheme="green" onClick={() => setShowFolderGroups(!showFolderGroups)}>
                  Folder Groups {showFolderGroups ? 'On' : 'Off'}
                </Button>
                <Button size="sm" variant={focusedView ? 'solid' : 'outline'} colorScheme="blue" onClick={() => setFocusedView(!focusedView)}>
                  Focus {focusedView ? 'On' : 'Off'}
                </Button>
                <Button size="sm" variant={enableZoom ? 'solid' : 'outline'} colorScheme="teal" onClick={() => setEnableZoom(!enableZoom)}>
                  Zoom {enableZoom ? 'On' : 'Off'}
                </Button>
                <Button size="sm" variant={highlightDocs ? 'solid' : 'outline'} colorScheme="purple" onClick={() => setHighlightDocs(!highlightDocs)}>
                  Highlight Docs {highlightDocs ? 'On' : 'Off'}
                </Button>
              </HStack>
              <HStack spacing={3} align="center">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Color Mode:</Text>
                {(['folder','type','commit-flow','activity','none'] as const).map((mode) => (
                  <Button key={mode} size="sm" variant={colorMode === mode ? 'solid' : 'outline'} onClick={() => setColorMode(mode)}>
                    {mode === 'folder' && 'By Folder'}
                    {mode === 'type' && 'By Type'}
                    {mode === 'commit-flow' && 'Commit Flow'}
                    {mode === 'activity' && 'By Activity'}
                    {mode === 'none' && 'Neutral'}
                  </Button>
                ))}
              </HStack>
              <HStack spacing={3} align="center">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Edge Emphasis</Text>
                <Slider value={Math.round(edgeEmphasis * 100)} onChange={(v)=> setEdgeEmphasis(v/100)} min={0} max={100} step={5} width="240px">
                  <SliderTrack bg={borderColor}><SliderFilledTrack bg="gray.400" /></SliderTrack>
                  <SliderThumb bg="gray.400" />
                </Slider>
              </HStack>
            </VStack>
          </VStack>
        </Box>

        {/* Main Visualization */}
        <Box border="1px solid" borderColor={borderColor} borderRadius="md" overflow="hidden">
          <ProgressiveStructureGraph
            commits={commits}
            currentTimeIndex={currentTimeIndex}
            width={1200}
            height={600}
            maxNodes={maxNodes}
            showFolderGroups={showFolderGroups}
            focusedView={focusedView}
            rangeStartIndex={range[0]}
            rangeEndIndex={range[1]}
            sizeByLOC={sizeByLOC}
            enableZoom={enableZoom}
            colorMode={colorMode}
            highlightDocs={highlightDocs}
            edgeEmphasis={edgeEmphasis}
            resetToken={resetToken}
          />
        </Box>
      </VStack>
    </Box>
  );
}
