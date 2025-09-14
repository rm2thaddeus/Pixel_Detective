'use client';

import React, { useState, useEffect } from 'react';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, Slider, SliderTrack, SliderFilledTrack, SliderThumb, HStack as ChakraHStack, Badge, useColorModeValue, RangeSlider, RangeSliderTrack, RangeSliderFilledTrack, RangeSliderThumb } from '@chakra-ui/react';
import ProgressiveStructureGraph from '../components/ProgressiveStructureGraph';
import dynamic from 'next/dynamic';
const WebGLEvolutionGraph = dynamic(() => import('../components/WebGLEvolutionGraph'), { ssr: false });

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
  const [playSpeedMs, setPlaySpeedMs] = useState(1800);
  const [performanceMode, setPerformanceMode] = useState<'balanced' | 'quality' | 'speed'>('balanced');
  const [renderEngine, setRenderEngine] = useState<'svg' | 'webgl'>('svg');
  const [activeFolders, setActiveFolders] = useState<string[]>([]);
  const [filterMode, setFilterMode] = useState<'dim' | 'hide'>('dim');
  const [patternInput, setPatternInput] = useState<string>("");
  // Phase A WebGL controls
  const [autoFit, setAutoFit] = useState(true);
  const [alwaysShowEdges, setAlwaysShowEdges] = useState(false);
  const [labelThreshold, setLabelThreshold] = useState(0.85);
  const [qualityLevel, setQualityLevel] = useState(0.6);

  // Build WebGL graph data (nodes/edges) from commits within the current range
  const webglData = React.useMemo(() => {
    if (!commits || commits.length === 0) return { nodes: [], relations: [] };
    const start = Math.max(0, Math.min(range[0], commits.length - 1));
    const upto = Math.max(start, Math.min(currentTimeIndex, Math.min(range[1], commits.length - 1)));
    const selected: Commit[] = commits.slice(start, upto + 1);

    // Folder filter helpers
    const active = new Set(activeFolders || []);
    const patterns = (patternInput || '').split(',').map(s => s.trim()).filter(Boolean);
    const matchesPatterns = (id: string) => {
      if (patterns.length === 0) return true;
      for (const p of patterns) {
        try {
          if (p.startsWith('/') && p.endsWith('/')) {
            const re = new RegExp(p.slice(1, -1));
            if (re.test(id)) return true;
          } else if (id.includes(p)) return true;
        } catch {}
      }
      return false;
    };
    const topFolderOf = (path: string) => {
      const norm = path.replace(/\\/g, '/');
      const idx = norm.indexOf('/');
      return idx === -1 ? norm : norm.slice(0, idx);
    };

    const nodes: any[] = [];
    const edges: any[] = [];
    const nodeSet = new Set<string>();

    // Add commit chain nodes
    for (let i = 0; i < selected.length; i++) {
      const c = selected[i];
      const totalLoc = (c.files || []).reduce((s, f) => s + Math.max(0, f.lines_after ?? f.loc ?? f.size ?? 0), 0);
      if (!nodeSet.has(c.hash)) {
        nodeSet.add(c.hash);
        nodes.push({ id: c.hash, label: c.hash.substring(0, 7), size: sizeByLOC ? Math.min(14, 7 + Math.sqrt(totalLoc) * 0.18) : 10, color: '#9f7aea', timestamp: c.timestamp, originalType: 'GitCommit', filesTouched: (c.files || []).length });
      }
      if (i > 0) {
        edges.push({ id: `${selected[i-1].hash}|${c.hash}`, from: selected[i-1].hash, to: c.hash, type: 'chain', color: '#8b5cf6', size: 1.6, timestamp: c.timestamp });
      }
    }

    // Aggregate and limit file nodes by frequency
    const fileMap = new Map<string, { file: FileChange; touches: number }>();
    for (const c of selected) {
      for (const f of c.files || []) {
        if (!f.path) continue;
        const top = topFolderOf(f.path);
        if (active.size > 0 && !active.has(top)) continue;
        if (!matchesPatterns(f.path)) continue;
        if (!fileMap.has(f.path)) fileMap.set(f.path, { file: f, touches: 0 });
        fileMap.get(f.path)!.touches += 1;
      }
    }

    const fileEntries = Array.from(fileMap.entries()).sort((a,b) => b[1].touches - a[1].touches);
    const budget = Math.max(0, maxNodes - nodes.length - 10);
    const picked = fileEntries.slice(0, budget);
    for (const [path, { file, touches }] of picked) {
      const loc = Math.max(0, file.lines_after ?? file.loc ?? file.size ?? 0);
      nodeSet.add(path);
      nodes.push({ id: path, label: path.split('/').pop(), size: sizeByLOC ? Math.min(12, 5 + Math.sqrt(loc) * 0.28) : 7, color: '#1c7ed6', folderPath: topFolderOf(path), originalType: file.type === 'document' ? 'Document' : 'File', touchCount: touches });
      // connect to all commits that touched this file in range
      for (const c of selected) {
        if ((c.files || []).some(cf => cf.path === path)) {
          edges.push({ id: `${c.hash}|${path}`, from: c.hash, to: path, type: 'touch', color: '#4a5568', size: 0.6, timestamp: c.timestamp });
        }
      }
    }

    return { nodes, relations: edges };
  }, [commits, range, currentTimeIndex, maxNodes, sizeByLOC, activeFolders, patternInput]);
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

        // Performance-optimized data loading based on commit count
        const filesPerCommit = performanceMode === 'speed' ? 20 : performanceMode === 'quality' ? 100 : 50;
        const commitLimit = performanceMode === 'speed' ? 1000 : performanceMode === 'quality' ? 5000 : 2500;
        
        console.log('TimelinePage: Performance mode:', performanceMode, 'Files per commit:', filesPerCommit, 'Commit limit:', commitLimit);
        
        // Request optimized data based on performance mode
        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/timeline?limit=${commitLimit}&max_files_per_commit=${filesPerCommit}`);
        
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

  // Performance-optimized autoplay with equilibration timing
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying && commits.length > 0 && range[1] > range[0]) {
      const baseSpeed = Math.max(200, playSpeedMs);
      
      // Calculate dynamic timing based on data complexity and performance mode
      const currentCommit = commits[currentTimeIndex];
      const filesInCommit = currentCommit?.files?.length || 1;
      const complexityFactor = Math.max(1, Math.log10(filesInCommit));
      const performanceFactor = performanceMode === 'speed' ? 0.5 : performanceMode === 'quality' ? 2.0 : 1.0;
      
      // Add equilibration time for complex commits
      const equilibrationTime = filesInCommit > 20 ? Math.max(baseSpeed * 0.3, baseSpeed * complexityFactor * performanceFactor * 0.1) : 0;
      const totalSpeed = baseSpeed + equilibrationTime;
      
      console.log('TimelinePage: Performance-optimized animation timing', {
        baseSpeed,
        filesInCommit,
        complexityFactor,
        performanceFactor,
        equilibrationTime,
        totalSpeed,
        performanceMode
      });
      
      interval = setInterval(() => {
        setCurrentTimeIndex(prev => {
          const next = prev + 1;
          if (next > range[1]) {
            setIsPlaying(false);
            return prev;
          }
          
          // Log equilibration for complex commits
          const nextCommit = commits[next];
          if (nextCommit?.files?.length > 20) {
            console.log('TimelinePage: Equilibration pause for complex commit', {
              commit: nextCommit.hash?.substring(0, 8),
              files: nextCommit.files.length,
              equilibrationTime: `${equilibrationTime}ms`
            });
          }
          
          return next;
        });
      }, totalSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, commits.length, range, playSpeedMs, currentTimeIndex, commits, performanceMode]);

  // Hotkeys: Space toggle play/pause, arrows navigate, '?' help overlay placeholder
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (isTyping) return;
      if (e.code === 'Space') { e.preventDefault(); setIsPlaying(p => !p); }
      if (e.code === 'ArrowRight') { e.preventDefault(); setCurrentTimeIndex(i => Math.min(i + 1, range[1])); }
      if (e.code === 'ArrowLeft') { e.preventDefault(); setCurrentTimeIndex(i => Math.max(i - 1, range[0])); }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [range]);

  // Derive top-level folders from loaded commits for grouping UI
  const topLevelFolders = React.useMemo(() => {
    const set = new Set<string>();
    for (const c of commits) {
      for (const f of c.files || []) {
        if (!f.path) continue;
        const norm = f.path.replace(/\\/g, '/');
        const idx = norm.indexOf('/');
        set.add(idx === -1 ? norm : norm.slice(0, idx));
      }
    }
    return Array.from(set).sort();
  }, [commits]);

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
          <HStack>
            <Text fontSize="sm" color={mutedTextColor}>Speed</Text>
            <Slider value={Math.round((4000 - playSpeedMs) / 40)} onChange={(v)=> setPlaySpeedMs(4000 - v*40)} min={10} max={100} step={5} width="160px">
              <SliderTrack bg={borderColor}><SliderFilledTrack bg="blue.400"/></SliderTrack>
              <SliderThumb bg="blue.400" />
            </Slider>
          </HStack>
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

              {/* Phase A — Parity polish toggles */}
              <HStack spacing={3} align="center">
                <Button size="sm" variant={autoFit ? 'solid' : 'outline'} onClick={() => setAutoFit(!autoFit)}>Auto‑fit {autoFit ? 'On' : 'Off'}</Button>
                <Button size="sm" variant={alwaysShowEdges ? 'solid' : 'outline'} onClick={() => setAlwaysShowEdges(!alwaysShowEdges)}>Always show edges {alwaysShowEdges ? 'On' : 'Off'}</Button>
                <HStack spacing={2} align="center">
                  <Text fontSize="sm" color={textColor}>Label threshold</Text>
                  <Slider value={Math.round(labelThreshold * 100)} onChange={(v)=> setLabelThreshold(v/100)} min={20} max={200} step={5} width="180px">
                    <SliderTrack bg={borderColor}><SliderFilledTrack bg="purple.400" /></SliderTrack>
                    <SliderThumb bg="purple.400" />
                  </Slider>
                </HStack>
              </HStack>

              {/* Phase B — Quality vs Speed */}
              <HStack spacing={3} align="center">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Quality vs Speed</Text>
                <Slider value={Math.round(qualityLevel * 100)} onChange={(v)=> setQualityLevel(v/100)} min={10} max={100} step={5} width="240px">
                  <SliderTrack bg={borderColor}><SliderFilledTrack bg="teal.400" /></SliderTrack>
                  <SliderThumb bg="teal.400" />
                </Slider>
                <Text fontSize="xs" color={mutedTextColor}>{qualityLevel < 0.45 ? 'Speed' : qualityLevel > 0.7 ? 'Quality' : 'Balanced'}</Text>
              </HStack>

              <HStack spacing={3} align="center">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Render Engine:</Text>
                <Button size="sm" variant={renderEngine==='svg'?'solid':'outline'} onClick={()=> setRenderEngine('svg')}>SVG</Button>
                <Button size="sm" variant={renderEngine==='webgl'?'solid':'outline'} onClick={()=> setRenderEngine('webgl')}>WebGL (CUDA)</Button>
                <Text fontSize="xs" color={mutedTextColor}>CUDA-accelerated renderer; optimized for large graphs</Text>
              </HStack>
              
              {/* Performance Mode Controls */}
              <HStack spacing={3} align="center">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Performance:</Text>
                <Button 
                  size="sm" 
                  variant={performanceMode === 'speed' ? 'solid' : 'outline'}
                  colorScheme="green"
                  onClick={() => setPerformanceMode('speed')}
                >
                  Speed
                </Button>
                <Button 
                  size="sm" 
                  variant={performanceMode === 'balanced' ? 'solid' : 'outline'}
                  colorScheme="blue"
                  onClick={() => setPerformanceMode('balanced')}
                >
                  Balanced
                </Button>
                <Button 
                  size="sm" 
                  variant={performanceMode === 'quality' ? 'solid' : 'outline'}
                  colorScheme="purple"
                  onClick={() => setPerformanceMode('quality')}
                >
                  Quality
                </Button>
                <Text fontSize="xs" color={mutedTextColor}>
                  {performanceMode === 'speed' ? 'Fast playback, fewer details' : 
                   performanceMode === 'quality' ? 'Full detail, slower playback' : 
                   'Optimized for most use cases'}
                </Text>
              </HStack>

              {/* Folder/Feature Grouping */}
              <VStack spacing={1} align="start">
                <Text fontSize="sm" fontWeight="medium" color={textColor}>Feature Groups</Text>
                <HStack spacing={2} wrap="wrap">
                  {topLevelFolders.slice(0, 18).map(folder => (
                    <Button key={folder} size="xs" variant={activeFolders.includes(folder) ? 'solid' : 'outline'} onClick={() => setActiveFolders(prev => prev.includes(folder) ? prev.filter(f=>f!==folder) : [...prev, folder])}>
                      {folder}
                    </Button>
                  ))}
                </HStack>
                <HStack spacing={2}>
                  <Button size="xs" onClick={() => setActiveFolders(topLevelFolders.slice(0, 18))}>Select All</Button>
                  <Button size="xs" onClick={() => setActiveFolders([])}>Clear</Button>
                  <Button size="xs" variant={filterMode==='hide' ? 'solid' : 'outline'} onClick={() => setFilterMode(filterMode==='hide'?'dim':'hide')}>
                    {filterMode==='hide' ? 'Hide Others' : 'Dim Others'}
                  </Button>
                </HStack>
                <HStack spacing={2}>
                  <Text fontSize="xs" color={mutedTextColor}>Include patterns (comma‑separated, supports /regex/):</Text>
                  <input value={patternInput} onChange={(e:any)=> setPatternInput(e.target.value)} placeholder="src/api,/^docs\\//" style={{ padding: '4px 6px', borderRadius: 6, border: `1px solid ${borderColor}`, background: 'transparent', color: textColor, width: '280px' }} />
                </HStack>
              </VStack>
            </VStack>
          </VStack>
        </Box>

        {/* Main Visualization */}
        <Box border="1px solid" borderColor={borderColor} borderRadius="md" overflow="hidden">
          {renderEngine === 'svg' ? (
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
            activeFolders={activeFolders}
            includePatterns={patternInput.split(',').map(s=>s.trim()).filter(Boolean)}
            filterMode={filterMode}
            resetToken={resetToken}
          />
          ) : (
            <>
              {console.log('TimelinePage: Attempting to render WebGL component with data:', {
                nodesCount: webglData.nodes?.length || 0,
                relationsCount: webglData.relations?.length || 0,
                hasValidData: (webglData.nodes?.length || 0) > 0
              })}
              <WebGLEvolutionGraph
                data={{ nodes: webglData.nodes, relations: webglData.relations }}
                width={1200}
                height={600}
                lightEdges
                focusMode={focusedView}
                layoutMode={'force'}
                edgeTypes={['chain','touch']}
                maxEdgesInView={2000}
                highlightNodeId={commits[currentTimeIndex]?.hash}
                currentCommitId={commits[currentTimeIndex]?.hash}
                colorMode={colorMode}
                highlightDocs={highlightDocs}
                edgeEmphasis={edgeEmphasis}
                autoFit={autoFit}
                alwaysShowEdges={alwaysShowEdges}
                labelThreshold={labelThreshold}
                qualityLevel={qualityLevel}
              />
            </>
          )}
        </Box>
      </VStack>
    </Box>
  );
}
