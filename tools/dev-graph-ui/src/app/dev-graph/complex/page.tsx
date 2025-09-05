'use client';
import dynamic from 'next/dynamic';
import { useRouter, useSearchParams } from 'next/navigation';
import { Box, Heading, Spinner, Alert, AlertIcon, Text, HStack, VStack, Switch, Slider, SliderFilledTrack, SliderThumb, SliderTrack, useDisclosure, Button, useToast, Tabs, TabList, TabPanels, Tab, TabPanel } from '@chakra-ui/react';
import { Select } from '@chakra-ui/react';
import { useMemo, useState, useEffect } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Header } from '@/components/Header';
import { Sprint } from '../components/SprintView';
import { useWindowedSubgraph, useCommitsBuckets, useAnalytics, useTelemetry, useFullTextSearch } from '../hooks/useWindowedSubgraph';
// Dynamic imports to avoid SSR issues
const TimelineView = dynamic(() => import('../components/CanvasTimeline'), { ssr: false });
const EnhancedTimelineView = dynamic(() => import('../components/EnhancedTimelineView').then(mod => ({ default: mod.EnhancedTimelineView })), { ssr: false });
const EvolutionGraph = dynamic(() => import('../components/EvolutionGraph'), { ssr: false });
const NodeDetailDrawer = dynamic(() => import('../components/NodeDetailDrawer'), { ssr: false });
const SearchBar = dynamic(() => import('../components/SearchBar'), { ssr: false });
const SprintView = dynamic(() => import('../components/SprintView').then(mod => ({ default: mod.SprintView })), { ssr: false });
const TemporalAnalytics = dynamic(() => import('../components/TemporalAnalytics').then(mod => ({ default: mod.TemporalAnalytics })), { ssr: false });
const TelemetryDisplay = dynamic(() => import('../components/TelemetryDisplay').then(mod => ({ default: mod.TelemetryDisplay })), { ssr: false });
// const RealAnalytics = dynamic(() => import('../components/RealAnalytics').then(mod => ({ default: mod.RealAnalytics })), { ssr: false });

// Removed react-force-graph usage in favor of Sigma.js (see EvolutionGraph)

// Developer Graph API base URL (configurable via env)
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

export default function DevGraphPage() {
	const PAGE_SIZE = 250; // Increased for better performance
	const [commitLimit, setCommitLimit] = useState(100);
	const router = useRouter();
	const searchParams = useSearchParams();
	const [layoutSeed, setLayoutSeed] = useState<number>(42);
	const [focusNodeId, setFocusNodeId] = useState<string | undefined>(undefined);
	
	// Phase 4: Use windowed subgraph as primary data source
	const windowedSubgraphQuery = useWindowedSubgraph({
		fromTimestamp: timeWindow.from,
		toTimestamp: timeWindow.to,
		nodeTypes: nodeTypeFilter.length > 0 ? nodeTypeFilter : undefined,
		limit: PAGE_SIZE,
		includeCounts: false // Skip counts for better performance
	});
	
	// Use new commits buckets API for timeline density
	const commitsBucketsQuery = useCommitsBuckets(
		'day',
		timeWindow.from,
		timeWindow.to,
		1000
	);

	// Analytics and telemetry
	const analyticsQuery = useAnalytics(timeWindow.from, timeWindow.to);
	const telemetryQuery = useTelemetry();
	const [ingesting, setIngesting] = useState(false);
	const [selectedNode, setSelectedNode] = useState<any>(null);
	const [selectedRange, setSelectedRange] = useState<{ start?: string; end?: string }>({});
	const [subgraph, setSubgraph] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
	const [selectedSprint, setSelectedSprint] = useState<Sprint | undefined>();
	
	// Phase 4: Performance queries
	const [timeWindow, setTimeWindow] = useState<{ from?: string; to?: string }>({});
	const [nodeTypeFilter, setNodeTypeFilter] = useState<string[]>([]);
	const [performanceMode, setPerformanceMode] = useState(false);
	const [layoutMode, setLayoutMode] = useState<'force' | 'time-radial'>('force');
	const [edgeTypes, setEdgeTypes] = useState<string[]>(['PART_OF','EVOLVES_FROM','REFERENCES','DEPENDS_ON']);
	const [maxEdgesInView, setMaxEdgesInView] = useState<number>(2000);
	
	// Phase 4: Progressive hydration state
	const [isHydrating, setIsHydrating] = useState(false);
	const [hydrationProgress, setHydrationProgress] = useState(0);

	// Deep link: initialize state from URL on mount, then persist updates back
	useEffect(() => {
		// Initialize from URL
		const mode = searchParams?.get('mode');
		const seed = searchParams?.get('seed');
		const from = searchParams?.get('from');
		const to = searchParams?.get('to');
		const focus = searchParams?.get('focus');

		if (mode === 'time') setLayoutMode('time-radial');
		if (mode === 'structure') setLayoutMode('force');
		if (seed && !Number.isNaN(Number(seed))) setLayoutSeed(Number(seed));
		if (from || to) setTimeWindow({ from: from || undefined, to: to || undefined });
		if (focus) setFocusNodeId(focus);
		// Persist last mode per user
		try {
			const savedMode = typeof window !== 'undefined' ? window.localStorage.getItem('devgraph:lastMode') : null;
			if (!mode && savedMode) setLayoutMode(savedMode === 'time' ? 'time-radial' : 'force');
			const savedSeed = typeof window !== 'undefined' ? window.localStorage.getItem('devgraph:layoutSeed') : null;
			if (!seed && savedSeed) setLayoutSeed(Number(savedSeed));
		} catch {}
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	// Persist to URL when key state changes
	useEffect(() => {
		const params = new URLSearchParams(searchParams?.toString());
		params.set('mode', layoutMode === 'time-radial' ? 'time' : 'structure');
		params.set('seed', String(layoutSeed));
		if (timeWindow.from) params.set('from', timeWindow.from); else params.delete('from');
		if (timeWindow.to) params.set('to', timeWindow.to); else params.delete('to');
		if (focusNodeId) params.set('focus', focusNodeId); else params.delete('focus');
		router.replace(`?${params.toString()}`);
		// Save last mode/seed
		try {
			if (typeof window !== 'undefined') {
				window.localStorage.setItem('devgraph:lastMode', layoutMode === 'time-radial' ? 'time' : 'structure');
				window.localStorage.setItem('devgraph:layoutSeed', String(layoutSeed));
			}
		} catch {}
	}, [layoutMode, layoutSeed, timeWindow.from, timeWindow.to, focusNodeId, router, searchParams]);
	
	// Enhanced timeline handlers
	const handleTimeRangeSelect = (fromTimestamp: string, toTimestamp: string) => {
		setTimeWindow({ from: fromTimestamp, to: toTimestamp });
		// Update the windowed subgraph query with new time range
		windowedSubgraphQuery.refetch();
	};
	
	const handleCommitSelect = (timestamp: string) => {
		// Set a narrow time window around the selected commit
		const date = new Date(timestamp);
		const startDate = new Date(date.getTime() - 24 * 60 * 60 * 1000); // 1 day before
		const endDate = new Date(date.getTime() + 24 * 60 * 60 * 1000); // 1 day after
		
		setTimeWindow({ 
			from: startDate.toISOString(), 
			to: endDate.toISOString() 
		});
		windowedSubgraphQuery.refetch();
	};
	
	const drawer = useDisclosure();
	const toast = useToast();

	// Sprints
	const sprintsQuery = useQuery({
		queryKey: ['dev-graph', 'sprints'],
		queryFn: async () => {
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/sprints`);
			if (!res.ok) throw new Error('Failed to load sprints');
			return res.json();
		},
		staleTime: 60_000,
	});

	const fetchSubgraph = async (startCommit?: string, endCommit?: string, offset: number = 0, append: boolean = false) => {
		const params = new URLSearchParams();
		if (startCommit) params.set('start_commit', startCommit);
		if (endCommit) params.set('end_commit', endCommit);
		params.set('limit', '800');
		params.set('offset', String(offset));
		const url = `${DEV_GRAPH_API_URL}/api/v1/dev-graph/subgraph/by-commits?${params.toString()}`;
		const res = await fetch(url);
		if (!res.ok) throw new Error('Failed to load time-bounded subgraph');
		const sg = await res.json();
		if (!append) {
			setSubgraph(sg);
			return;
		}
		// Append with de-duplication
		setSubgraph(prev => {
			const seenNode = new Set((prev.nodes || []).map((n: any) => n.id));
			const mergedNodes = [...prev.nodes, ...((sg.nodes || []).filter((n: any) => !seenNode.has(n.id)))];
			const seenEdge = new Set((prev.links || []).map((l: any) => `${l.from}|${l.to}|${l.type}|${l.timestamp || ''}`));
			const newEdges = (sg.links || []).filter((l: any) => !seenEdge.has(`${l.from}|${l.to}|${l.type}|${l.timestamp || ''}`));
			return { nodes: mergedNodes, links: [...prev.links, ...newEdges] };
		});
	};

	// Progressive hydration effect
	useEffect(() => {
		if (!windowedSubgraphQuery.data?.pages) return;
		
		setIsHydrating(true);
		setHydrationProgress(0);
		
		// Process data in batches using requestIdleCallback
		const processBatches = () => {
			const allPages = windowedSubgraphQuery.data?.pages || [];
			let allNodes: any[] = [];
			let allEdges: any[] = [];
			
			// Flatten all pages
			allPages.forEach(page => {
				allNodes = [...allNodes, ...(page.nodes || [])];
				allEdges = [...allEdges, ...(page.edges || [])];
			});
			
			const batchSize = 200;
			let processed = 0;
			
			const processBatch = () => {
				const start = processed;
				const end = Math.min(processed + batchSize, allNodes.length);
				const batch = allNodes.slice(start, end);
				
				// Process batch (add coordinates, validate, etc.)
				batch.forEach((node: any, index: number) => {
					// Add deterministic coordinates if missing
					if (typeof node.x !== 'number' || isNaN(node.x) || typeof node.y !== 'number' || isNaN(node.y)) {
						const hash = node.id.split('').reduce((a: number, b: string) => {
							a = ((a << 5) - a) + b.charCodeAt(0);
							return a & a;
						}, 0);
						node.x = Math.abs(hash % 1000);
						node.y = Math.abs((hash >> 8) % 1000);
					}
				});
				
				processed = end;
				const progress = Math.min(100, (processed / allNodes.length) * 100);
				setHydrationProgress(progress);
				
				if (processed < allNodes.length) {
					// Use requestIdleCallback for non-blocking processing
					if (window.requestIdleCallback) {
						window.requestIdleCallback(processBatch, { timeout: 100 });
					} else {
						setTimeout(processBatch, 0);
					}
				} else {
					setIsHydrating(false);
					setHydrationProgress(100);
				}
			};
			
			processBatch();
		};
		
		processBatches();
	}, [windowedSubgraphQuery.data]);

	const data = useMemo(
		() => {
			// Phase 4: Use windowed subgraph for better performance
			let rawNodes: any[] = [];
			let rawRelations: any[] = [];
			
			// Prioritize windowed subgraph data if available
			if (windowedSubgraphQuery.data?.pages?.[0]) {
				// Flatten all pages for progressive loading
				windowedSubgraphQuery.data.pages.forEach(page => {
					rawNodes = [...rawNodes, ...(page.nodes || [])];
					rawRelations = [...rawRelations, ...(page.edges || [])];
				});
			} else if (selectedRange.start || selectedRange.end) {
				// Fallback to legacy subgraph
				rawNodes = subgraph.nodes ?? [];
				rawRelations = subgraph.links ?? [];
			}
			
			// Add coordinates to nodes that don't have them
			const nodesWithCoords = rawNodes.map((node: any, index: number) => {
				// Use deterministic positioning based on node ID hash for consistent layout
				const hash = node.id.split('').reduce((a: number, b: string) => {
					a = ((a << 5) - a) + b.charCodeAt(0);
					return a & a;
				}, 0);
				
				// Calculate coordinates with additional validation
				let x = typeof node.x === 'number' && !isNaN(node.x) && isFinite(node.x) ? node.x : Math.abs(hash % 1000);
				let y = typeof node.y === 'number' && !isNaN(node.y) && isFinite(node.y) ? node.y : Math.abs((hash >> 8) % 1000);
				const size = typeof node.size === 'number' && !isNaN(node.size) && isFinite(node.size) ? node.size : 1;
				
				// Final validation to ensure coordinates are valid
				if (!isFinite(x) || x < -10000 || x > 10000) {
					console.warn(`Invalid x coordinate for node ${node.id}, using fallback`);
					x = Math.abs(hash % 1000);
				}
				if (!isFinite(y) || y < -10000 || y > 10000) {
					console.warn(`Invalid y coordinate for node ${node.id}, using fallback`);
					y = Math.abs((hash >> 8) % 1000);
				}
				
				return {
					...node,
					x,
					y,
					size,
				};
			});
			
			// Data preprocessing complete
			
			return {
				nodes: nodesWithCoords,
				relations: rawRelations,
			};
		},
		[windowedSubgraphQuery.data, nodesQuery.data, relationsQuery.data, selectedRange, subgraph]
	);

	const [showEvolves, setShowEvolves] = useState(true);
	const [showViewportOnly, setShowViewportOnly] = useState(false);
	const [enableClustering, setEnableClustering] = useState(false);
	const [lightEdges, setLightEdges] = useState(true);
	const [focusMode, setFocusMode] = useState(true);
	const [enablePhysics, setEnablePhysics] = useState(false);

	const filteredData = useMemo(() => {
		const baseNodes = data.nodes ?? [];
		const nodeIds = new Set((baseNodes ?? []).map((n: any) => n.id));
		const baseRelations = (data as any).relations ?? [];
		return {
			nodes: baseNodes,
			relations: baseRelations
				.filter((l: any) => showEvolves ? true : l.type !== 'EVOLVES_FROM')
				.filter((l: any) => nodeIds.has(l.from) && nodeIds.has(l.to)),
		};
	}, [data, showEvolves]);

	// Graph data ready for rendering

	// Data validation
	const isValidData = (filteredData.nodes?.length ?? 0) > 0 && (((filteredData as any).relations)?.length ?? 0) > 0;
	const hasValidRelations = (((filteredData as any).relations) ?? []).every((link: any) => 
		link.from && link.to && link.type && 
		(filteredData.nodes ?? []).some((node: any) => node.id === link.from) &&
		(filteredData.nodes ?? []).some((node: any) => node.id === link.to)
	);

	return (
		<Box minH="100vh">
			<Header />
			<Box p={8}>
				<Heading mb={4}>Developer Graph - Complex View</Heading>
				
				{/* Simple Navigation */}
				<Box mb={6} p={4} bg="gray.50" borderRadius="md">
					<Text fontSize="sm" fontWeight="medium" mb={2}>Navigate to other views:</Text>
					<HStack spacing={4}>
						<Text fontSize="sm" color="blue.600" fontWeight="bold">Complex View (Current)</Text>
						<Text fontSize="sm">•</Text>
						<Text fontSize="sm" color="green.600"><a href="/dev-graph/enhanced">Enhanced Dashboard</a></Text>
						<Text fontSize="sm">•</Text>
						<Text fontSize="sm" color="purple.600"><a href="/dev-graph/simple">Simple Dashboard</a></Text>
					</HStack>
				</Box>
				
				{/* Debug Info */}
				<Box mb={4} p={4} bg="gray.100" borderRadius="md" fontSize="sm">
					<Text fontWeight="bold">Debug Info:</Text>
					<Text>Nodes loaded: {windowedSubgraphQuery.data?.pages?.reduce((acc: number, p: any) => acc + (p.nodes?.length || 0), 0) || 0}</Text>
					<Text>Edges loaded: {windowedSubgraphQuery.data?.pages?.reduce((acc: number, p: any) => acc + (p.edges?.length || 0), 0) || 0}</Text>
					<Text>Commits buckets: {commitsBucketsQuery.data?.buckets?.length || 0}</Text>
					<Text>Data valid: {isValidData ? 'Yes' : 'No'}</Text>
					<Text>Relations valid: {hasValidRelations ? 'Yes' : 'No'}</Text>
					<Text>Performance mode: {performanceMode ? 'Enabled' : 'Disabled'}</Text>
					<Text>Time window: {timeWindow.from ? new Date(timeWindow.from).toLocaleDateString() : 'None'} - {timeWindow.to ? new Date(timeWindow.to).toLocaleDateString() : 'None'}</Text>
					{isHydrating && (
						<Text color="blue.600">
							Hydrating: {Math.round(hydrationProgress)}% complete
						</Text>
					)}
					{/* Phase 4: Performance metrics */}
					{windowedSubgraphQuery.data?.pages?.[0]?.performance && (
						<Text color="green.600">
							Subgraph: {windowedSubgraphQuery.data.pages[0].performance.query_time_ms}ms 
							({windowedSubgraphQuery.data.pages[0].pagination.returned_nodes} nodes, 
							{windowedSubgraphQuery.data.pages[0].pagination.returned_edges} edges)
							{windowedSubgraphQuery.data.pages[0].performance.cache_hit && ' (cached)'}
						</Text>
					)}
					{commitsBucketsQuery.data?.performance && (
						<Text color="blue.600">
							Timeline: {commitsBucketsQuery.data.performance.query_time_ms}ms 
							({commitsBucketsQuery.data.performance.total_buckets} buckets)
						</Text>
					)}
					{telemetryQuery.data && (
						<Text color="purple.600">
							Telemetry: {telemetryQuery.data.avg_query_time_ms}ms avg, 
							{Math.round(telemetryQuery.data.cache_hit_rate * 100)}% cache hit, 
							{telemetryQuery.data.memory_usage_mb}MB memory
						</Text>
					)}
					{!hasValidRelations && (((data as any).relations)?.length ?? 0) > 0 && (
						<Text color="red">
							Invalid relations: {(data as any).relations.filter((link: any) => 
								!link.from || !link.to || !link.type ||
								!(data.nodes ?? []).some((node: any) => node.id === link.from) ||
								!(data.nodes ?? []).some((node: any) => node.id === link.to)
							).length} found
						</Text>
					)}
				</Box>

				{/* Graph Controls */}
				<HStack mb={4} spacing={6} wrap="wrap">
					{/* Mode Toggle */}
					<HStack>
						<Text fontSize="sm" fontWeight="semibold">Mode</Text>
						<HStack spacing={1}>
							<Button size="sm" variant={layoutMode === 'force' ? 'solid' : 'outline'} onClick={() => { setLayoutMode('force'); setFocusNodeId(undefined); }}>Structure</Button>
							<Button size="sm" variant={layoutMode === 'time-radial' ? 'solid' : 'outline'} onClick={() => { setLayoutMode('time-radial'); }}>Time</Button>
						</HStack>
					</HStack>

					{/* Layout seed */}
					<HStack>
						<Text fontSize="sm">Layout seed</Text>
						<Button size="xs" onClick={() => setLayoutSeed((s) => (s + 1) % 100000)}>Reseed</Button>
						<Text fontSize="xs" color="gray.600">{layoutSeed}</Text>
					</HStack>
					<HStack>
						<Text fontSize="sm">Light edges</Text>
						<Switch size="sm" isChecked={lightEdges} onChange={(e) => setLightEdges(e.target.checked)} />
					</HStack>
					<HStack>
						<Text fontSize="sm">Focus mode</Text>
						<Switch size="sm" isChecked={focusMode} onChange={(e) => setFocusMode(e.target.checked)} />
					</HStack>
					<HStack>
						<Text fontSize="sm">Viewport-only</Text>
						<Switch size="sm" isChecked={showViewportOnly} onChange={(e) => setShowViewportOnly(e.target.checked)} />
					</HStack>
					<HStack>
						<Text fontSize="sm">Clustering</Text>
						<Switch size="sm" isChecked={enableClustering} onChange={(e) => setEnableClustering(e.target.checked)} />
					</HStack>
					<HStack>
						<Text fontSize="sm">Physics</Text>
						<Switch size="sm" isChecked={enablePhysics} onChange={(e) => setEnablePhysics(e.target.checked)} />
					</HStack>
					{/* Layout select replaced by Mode toggle above to align with PRD */}
					<HStack>
						<Text fontSize="sm">Max edges</Text>
						<Slider aria-label='max-edges' min={200} max={8000} step={200} value={maxEdgesInView} onChange={setMaxEdgesInView} width={200}>
							<SliderTrack><SliderFilledTrack /></SliderTrack>
							<SliderThumb />
						</Slider>
						<Text fontSize="sm" width={12}>{maxEdgesInView}</Text>
					</HStack>
					<HStack>
						<Text fontSize="sm">Edges</Text>
						{['PART_OF','EVOLVES_FROM','REFERENCES','DEPENDS_ON'].map(t => (
							<HStack key={t}>
								<Switch size="sm" isChecked={edgeTypes.includes(t)} onChange={(e) => setEdgeTypes(prev => e.target.checked ? [...prev, t] : prev.filter(x => x !== t))} />
								<Text fontSize="xs">{t}</Text>
							</HStack>
						))}
					</HStack>
					<HStack>
						<Text fontSize="sm">Performance mode</Text>
						<Switch size="sm" isChecked={performanceMode} onChange={(e) => setPerformanceMode(e.target.checked)} />
					</HStack>
					<HStack>
						<Switch isChecked={showEvolves} onChange={(e) => setShowEvolves(e.target.checked)} />
						<Text fontSize="sm">Show EVOLVES_FROM</Text>
					</HStack>
					<HStack flex={1} pl={6} pr={2}>
						<Text fontSize="sm" color="gray.600">Commits:</Text>
						<Slider aria-label='commit-limit' min={20} max={500} step={10} value={commitLimit} onChange={setCommitLimit}>
							<SliderTrack>
								<SliderFilledTrack />
							</SliderTrack>
							<SliderThumb />
						</Slider>
						<Text fontSize="sm" width={10}>{commitLimit}</Text>
					</HStack>
					<Button isLoading={ingesting} onClick={async () => {
						try {
							setIngesting(true);
							await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/ingest/recent?limit=100`, { method: 'POST' });
							await Promise.all([
								windowedSubgraphQuery.refetch(),
								commitsBucketsQuery.refetch(),
								analyticsQuery.refetch(),
								telemetryQuery.refetch(),
							]);
						} catch (e) {
							console.error('Ingest failed', e);
						} finally {
							setIngesting(false);
						}
					}} colorScheme="blue">
						Ingest Latest
					</Button>
				</HStack>

				{/* Search */}
				<Box mb={3}>
					<SearchBar onSearch={async (q, filters) => {
						try {
							// Build search query with filters
							const params = new URLSearchParams();
							params.set('q', q);
							if (filters.nodeType) params.set('node_type', filters.nodeType);
							if (filters.relationshipType) params.set('relationship_type', filters.relationshipType);
							
							const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/search?${params.toString()}`);
							if (!res.ok) throw new Error('Search failed');
							const nodes = await res.json();
							
							// Show only found nodes and their existing links from current dataset
							const nodeIds = new Set(nodes.map((n: any) => n.id));
							const links = (selectedRange.start || selectedRange.end ? subgraph.links : ((relationsQuery.data?.pages || []).flat())) || [];
							const filteredLinks = links.filter((l: any) => nodeIds.has(l.from) || nodeIds.has(l.to));
							
							setSubgraph({ nodes, links: filteredLinks });
							setSelectedRange({});
							
							// Search results processed
						} catch (e) {
							console.error('Search failed:', e);
						}
					}} />
				</Box>

				{/* Temporal Views Tabs */}
				<Box mb={4}>
					<Tabs variant="enclosed" colorScheme="green">
						<TabList>
							<Tab>Timeline View</Tab>
							<Tab>Enhanced Timeline</Tab>
							<Tab>Sprint View</Tab>
							<Tab>Analytics</Tab>
						</TabList>
						
						<TabPanels>
							{/* Timeline Tab */}
							<TabPanel>
								<TimelineView
									events={(Array.isArray(commitsQuery.data) ? commitsQuery.data : [])
										.filter((c: any) => c && c.hash && c.timestamp)
										.map((c: any) => ({
											id: c.hash,
											title: c.message || 'Untitled Commit',
											timestamp: c.timestamp,
											author: c.author_email || 'Unknown Author',
											type: 'commit',
											commit_hash: c.hash,
											files_changed: c.files_changed || [],
										}))}
									onSelect={(ev) => {
										// Toggle range selection: first click sets start, second sets end and fetches subgraph
										if (!selectedRange.start || (selectedRange.start && selectedRange.end)) {
											setSelectedRange({ start: ev.id, end: undefined });
										} else if (selectedRange.start && !selectedRange.end) {
											const start = selectedRange.start;
											const end = ev.id;
											setSelectedRange({ start, end });
											fetchSubgraph(start, end).catch(console.error);
										}
									}}
									onRangeSelect={(startId, endId) => {
										setSelectedRange({ start: startId, end: endId });
										fetchSubgraph(startId, endId).catch(console.error);
									}}
									onTimeScrub={(timestamp) => {
										// Time scrubber functionality: highlight nodes active at this timestamp
										// Time scrubbing to timestamp
										// TODO: Implement graph filtering based on timestamp
										// This will be enhanced in the next iteration
									}}
								/>
								<HStack mt={2}>
									<Button size="sm" onClick={() => nodesQuery.fetchNextPage()}>Load more nodes</Button>
									<Button size="sm" onClick={() => relationsQuery.fetchNextPage()}>Load more relations</Button>
									{selectedRange.start && selectedRange.end && (
										<Button size="sm" onClick={() => { const next = (subgraph as any)._offset ? (subgraph as any)._offset + 800 : 800; (subgraph as any)._offset = next; fetchSubgraph(selectedRange.start, selectedRange.end, next, true).catch(console.error); }}>Load more in range</Button>
									)}
								</HStack>
							</TabPanel>
							
							{/* Enhanced Timeline Tab */}
							<TabPanel>
								<EnhancedTimelineView
									onTimeRangeSelect={handleTimeRangeSelect}
									onCommitSelect={handleCommitSelect}
									height={300}
								/>
								{/* Subgraph Preview */}
								{windowedSubgraphQuery.data?.pages?.[0] && (
									<Box mt={4} p={4} bg="gray.50" borderRadius="md" borderWidth={1}>
										<Text fontSize="sm" fontWeight="bold" mb={2}>Subgraph Preview</Text>
										<Text fontSize="xs" color="gray.600">
											{windowedSubgraphQuery.data.pages[0].pagination.returned_nodes} nodes, 
											{windowedSubgraphQuery.data.pages[0].pagination.returned_edges} edges
											{windowedSubgraphQuery.data.pages[0].performance && (
												<span> • {windowedSubgraphQuery.data.pages[0].performance.query_time_ms}ms</span>
											)}
										</Text>
										<Box mt={3}>
											{(() => {
												const pg: any = windowedSubgraphQuery.data!.pages[0];
												const nodes = (pg.nodes || []).slice(0, 200);
												const relations = (pg.edges || []).slice(0, 300);
												return (
                                            <EvolutionGraph 
														data={{ nodes, relations }} 
														height={220}
														lightEdges
														focusMode={false}
														enablePhysics={enablePhysics}
														layoutMode={layoutMode}
														edgeTypes={edgeTypes}
														maxEdgesInView={maxEdgesInView}
													/>
												);
											})()}
										</Box>
									</Box>
								)}
							</TabPanel>
							
							{/* Sprint Tab */}
							<TabPanel>
								{sprintsQuery.isLoading && <Text>Loading sprints…</Text>}
								{sprintsQuery.error && (
									<Alert status="error" mb={2}><AlertIcon />{(sprintsQuery.error as Error).message}</Alert>
								)}
								{Array.isArray(sprintsQuery.data) && (
									<SprintView
										sprints={sprintsQuery.data}
										onSprintSelect={(sprint) => {
											setSelectedSprint(sprint);
											fetchSubgraph(sprint.commit_range.start || undefined, sprint.commit_range.end || undefined).catch(console.error);
										}}
										selectedSprint={selectedSprint}
									/>
								)}
							</TabPanel>
							
							{/* Analytics Tab */}
							<TabPanel>
								<VStack spacing={4} align="stretch">
									{/* System Status */}
									<TelemetryDisplay />
									
									{/* Analytics Placeholder */}
									<Box p={6} bg="gray.50" borderRadius="md" borderWidth={1}>
										<Text fontSize="lg" fontWeight="bold" mb={4}>Analytics</Text>
										<Text color="gray.600" mb={4}>
											Analytics features are temporarily disabled while we update the backend API.
										</Text>
										<Text fontSize="sm" color="gray.500">
											The evolutionary tree visualization and other core features are fully functional.
										</Text>
									</Box>
								</VStack>
							</TabPanel>
						</TabPanels>
					</Tabs>
					
					{(selectedRange.start || selectedRange.end) && (
						<HStack mt={2} spacing={3}>
							<Text fontSize="sm" color="gray.600">Selected window: {selectedRange.start} → {selectedRange.end || '…'}</Text>
							<Button size="sm" onClick={() => { setSelectedRange({}); setSubgraph({ nodes: [], links: [] }); }}>Clear</Button>
						</HStack>
					)}
				</Box>
                <Box mb={3} fontSize="sm">
                    <Text fontWeight="bold" mb={1}>Node Legend</Text>
                    <Box display="flex" alignItems="center" gap={2} mb={2}>
                        <Text fontSize="xs" color="gray.600">Degree</Text>
                        <Box flex="1" height="8px" borderRadius="md" bgGradient="linear(to-r, #440154, #3b528b, #21918c, #5ec962, #fde725)" />
                        <Text fontSize="xs" color="gray.600">Low</Text>
                        <Text fontSize="xs" color="gray.600">High</Text>
                    </Box>
                    <Text fontSize="xs" color="gray.600" mb={2}>Node size: proportional to degree</Text>
                    <Text><span style={{ color: '#888' }}>■</span> PART_OF</Text>
                    <Text><span style={{ color: '#2b8a3e' }}>■</span> EVOLVES_FROM</Text>
                    <Text><span style={{ color: '#1c7ed6' }}>■</span> REFERENCES</Text>
                    <Text><span style={{ color: '#e67700' }}>■</span> DEPENDS_ON</Text>
                </Box>

				{(windowedSubgraphQuery.isLoading || commitsBucketsQuery.isLoading) && (
					<Box display="flex" alignItems="center" gap={2} mb={4}>
						<Spinner size="sm" />
						Loading graph data...
						{isHydrating && (
							<Text fontSize="sm" color="blue.600">
								({Math.round(hydrationProgress)}% hydrated)
							</Text>
						)}
					</Box>
				)}
				
				{(windowedSubgraphQuery.error || commitsBucketsQuery.error) && (
					<Alert status="error" mb={4}>
						<AlertIcon />
						{(windowedSubgraphQuery.error as Error)?.message || (commitsBucketsQuery.error as Error)?.message || 'Failed to load graph data'}
					</Alert>
				)}
				
					{isValidData && hasValidRelations && (
						<EvolutionGraph 
							data={filteredData}
							layoutSeed={layoutSeed}
							focusNodeId={focusNodeId}
							onNodeClick={(n: any) => {
								setSelectedNode(n);
								// Escape hatches per PRD
								if (layoutMode === 'time-radial') {
									setLayoutMode('force');
									setFocusNodeId(String(n.id));
								} else {
									setLayoutMode('time-radial');
									// If timestamp available, set narrow time window around it
									const t = (n.timestamp || n.created_at || n.time) ? new Date(n.timestamp || n.created_at || n.time).getTime() : undefined;
									if (t) {
										const start = new Date(t - 24*60*60*1000).toISOString();
										const end = new Date(t + 24*60*60*1000).toISOString();
										setTimeWindow({ from: start, to: end });
									}
								}
								drawer.onOpen();
							}}
							currentTimestamp={selectedRange.start ? commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp : undefined}
							timeRange={timeWindow.from && timeWindow.to ? { start: timeWindow.from, end: timeWindow.to } : (selectedRange.start && selectedRange.end ? {
								start: commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp || '',
								end: commitsQuery.data?.find((c: any) => c.hash === selectedRange.end)?.timestamp || ''
							} : undefined)}
							enableClustering={enableClustering}
							enablePhysics={enablePhysics}
							layoutMode={layoutMode}
							edgeTypes={edgeTypes}
							maxEdgesInView={maxEdgesInView}
							showOnlyViewport={showViewportOnly}
							lightEdges={lightEdges}
							focusMode={focusMode}
							onViewportChange={({ zoom }) => {
								// Simple heuristic: if zoomed in beyond threshold, load more pages
								// Only fetch if we haven't already fetched all pages
								if (zoom > 1.5 && nodesQuery.hasNextPage && relationsQuery.hasNextPage) {
									nodesQuery.fetchNextPage();
									relationsQuery.fetchNextPage();
								}
							}}
						/>
					)}
				
				{!isValidData && !nodesQuery.isLoading && (
					<Alert status="info">
						<AlertIcon />
						No graph data available. Please check if the Developer Graph API is running.
					</Alert>
				)}
				
					{isValidData && !hasValidRelations && (
						<Alert status="warning">
							<AlertIcon />
							Graph data loaded but some relations reference non-existent nodes. Check the debug info above.
						</Alert>
					)}
			</Box>
			<NodeDetailDrawer isOpen={drawer.isOpen} onClose={drawer.onClose} node={selectedNode} />
		</Box>
	);
}
