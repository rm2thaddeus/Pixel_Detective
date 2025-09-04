'use client';
import dynamic from 'next/dynamic';
import { Box, Heading, Spinner, Alert, AlertIcon, Text, HStack, Switch, Slider, SliderFilledTrack, SliderThumb, SliderTrack, useDisclosure, Button, useToast, Tabs, TabList, TabPanels, Tab, TabPanel } from '@chakra-ui/react';
import { Select } from '@chakra-ui/react';
import { useMemo, useState, useEffect } from 'react';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { Header } from '@/components/Header';
import { Sprint } from '../components/SprintView';
import { useWindowedSubgraph, useCommitsBuckets } from '../hooks/useWindowedSubgraph';
// Dynamic imports to avoid SSR issues
const TimelineView = dynamic(() => import('../components/CanvasTimeline'), { ssr: false });
const EnhancedTimelineView = dynamic(() => import('../components/EnhancedTimelineView').then(mod => ({ default: mod.EnhancedTimelineView })), { ssr: false });
const EvolutionGraph = dynamic(() => import('../components/EvolutionGraph'), { ssr: false });
const NodeDetailDrawer = dynamic(() => import('../components/NodeDetailDrawer'), { ssr: false });
const SearchBar = dynamic(() => import('../components/SearchBar'), { ssr: false });
const SprintView = dynamic(() => import('../components/SprintView').then(mod => ({ default: mod.SprintView })), { ssr: false });
const TemporalAnalytics = dynamic(() => import('../components/TemporalAnalytics').then(mod => ({ default: mod.TemporalAnalytics })), { ssr: false });
// const RealAnalytics = dynamic(() => import('../components/RealAnalytics').then(mod => ({ default: mod.RealAnalytics })), { ssr: false });

// Removed react-force-graph usage in favor of Sigma.js (see EvolutionGraph)

// Developer Graph API base URL (configurable via env)
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

export default function DevGraphPage() {
	const PAGE_SIZE = 200;
	const [commitLimit, setCommitLimit] = useState(100);
	
	const nodesQuery = useInfiniteQuery({
		queryKey: ['dev-graph', 'nodes', PAGE_SIZE],
		queryFn: async ({ pageParam = 0 }) => {
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes?limit=${PAGE_SIZE}&offset=${pageParam}`);
			if (!res.ok) throw new Error('Failed to load nodes');
			return res.json();
		},
		initialPageParam: 0,
		getNextPageParam: (_lastPage, allPages) => allPages.length * PAGE_SIZE,
		staleTime: 60_000,
		enabled: true, // Enable automatic fetching
	});

	const relationsQuery = useInfiniteQuery({
		queryKey: ['dev-graph', 'relations', PAGE_SIZE],
		queryFn: async ({ pageParam = 0 }) => {
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations?limit=${PAGE_SIZE}&offset=${pageParam}`);
			if (!res.ok) throw new Error('Failed to load relations');
			return res.json();
		},
		initialPageParam: 0,
		getNextPageParam: (_lastPage, allPages) => allPages.length * PAGE_SIZE,
		staleTime: 60_000,
		enabled: true, // Enable automatic fetching
	});

	const commitsQuery = useQuery({
		queryKey: ['dev-graph', 'commits', commitLimit],
		queryFn: async () => {
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=${commitLimit}`);
			if (!res.ok) throw new Error('Failed to load commits');
			return res.json();
		},
		staleTime: 5 * 60 * 1000,
		enabled: true, // Enable automatic fetching
	});
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
	
	// Use new windowed subgraph API for better performance
	const windowedSubgraphQuery = useWindowedSubgraph({
		fromTimestamp: timeWindow.from,
		toTimestamp: timeWindow.to,
		nodeTypes: nodeTypeFilter.length > 0 ? nodeTypeFilter : undefined,
		limit: performanceMode ? 2000 : 1000 // Higher limit in performance mode
	});
	
	// Use new commits buckets API for timeline density
	const commitsBucketsQuery = useCommitsBuckets(
		'day',
		timeWindow.from,
		timeWindow.to,
		1000
	);
	
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

	const data = useMemo(
		() => {
			// Phase 4: Use windowed subgraph for better performance
			let rawNodes: any[] = [];
			let rawRelations: any[] = [];
			
			// Prioritize windowed subgraph data if available
			if (windowedSubgraphQuery.data?.pages?.[0]) {
				const windowedData = windowedSubgraphQuery.data.pages[0];
				rawNodes = windowedData.nodes || [];
				rawRelations = windowedData.edges || [];
			} else if (selectedRange.start || selectedRange.end) {
				// Fallback to legacy subgraph
				rawNodes = subgraph.nodes ?? [];
				rawRelations = subgraph.links ?? [];
			} else {
				// Fallback to full graph data
				rawNodes = (nodesQuery.data?.pages || []).flat();
				rawRelations = (relationsQuery.data?.pages || []).flat();
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
					<Text>Nodes loaded: {((nodesQuery.data?.pages as any[] | undefined) || []).reduce((acc: number, p: any[]) => acc + p.length, 0)}</Text>
					<Text>Relations loaded: {((relationsQuery.data?.pages as any[] | undefined) || []).reduce((acc: number, p: any[]) => acc + p.length, 0)}</Text>
					<Text>Commits loaded: {Array.isArray(commitsQuery.data) ? commitsQuery.data.length : 0}</Text>
					<Text>Data valid: {isValidData ? 'Yes' : 'No'}</Text>
					<Text>Relations valid: {hasValidRelations ? 'Yes' : 'No'}</Text>
					<Text>Performance mode: {performanceMode ? 'Enabled' : 'Disabled'}</Text>
					<Text>Time window: {timeWindow.from ? new Date(timeWindow.from).toLocaleDateString() : 'None'} - {timeWindow.to ? new Date(timeWindow.to).toLocaleDateString() : 'None'}</Text>
					{/* Phase 4: Performance metrics */}
					{windowedSubgraphQuery.data?.pages?.[0]?.performance && (
						<Text color="green.600">
							Performance: {windowedSubgraphQuery.data.pages[0].performance.query_time_ms}ms 
							({windowedSubgraphQuery.data.pages[0].pagination.returned_nodes} nodes, 
							{windowedSubgraphQuery.data.pages[0].pagination.returned_edges} edges)
						</Text>
					)}
					{commitsBucketsQuery.data?.performance && (
						<Text color="blue.600">
							Timeline: {commitsBucketsQuery.data.performance.query_time_ms}ms 
							({commitsBucketsQuery.data.performance.total_buckets} buckets)
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
					<HStack>
						<Text fontSize="sm">Layout</Text>
						<Select size="sm" value={layoutMode} onChange={(e) => setLayoutMode(e.target.value as any)}>
							<option value="force">Force</option>
							<option value="time-radial">Time-Radial</option>
						</Select>
					</HStack>
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
								nodesQuery.refetch(),
								relationsQuery.refetch(),
								commitsQuery.refetch(),
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
								<Box p={6} bg="gray.50" borderRadius="md" borderWidth={1}>
									<Text fontSize="lg" fontWeight="bold" mb={4}>Analytics</Text>
									<Text color="gray.600" mb={4}>
										Analytics features are temporarily disabled while we update the backend API.
									</Text>
									<Text fontSize="sm" color="gray.500">
										The evolutionary tree visualization and other core features are fully functional.
									</Text>
								</Box>
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

				{(nodesQuery.isLoading || relationsQuery.isLoading) && (
					<Box display="flex" alignItems="center" gap={2} mb={4}>
						<Spinner size="sm" />
						Loading graph...
					</Box>
				)}
				
				{(nodesQuery.error || relationsQuery.error) && (
					<Alert status="error" mb={4}>
						<AlertIcon />
						{(nodesQuery.error as Error)?.message || (relationsQuery.error as Error)?.message || 'Failed to load graph'}
					</Alert>
				)}
				
					{isValidData && hasValidRelations && (
						<EvolutionGraph 
							data={filteredData}
							onNodeClick={(n: any) => { setSelectedNode(n); drawer.onOpen(); }}
							currentTimestamp={selectedRange.start ? commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp : undefined}
							timeRange={selectedRange.start && selectedRange.end ? {
								start: commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp || '',
								end: commitsQuery.data?.find((c: any) => c.hash === selectedRange.end)?.timestamp || ''
							} : undefined}
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
