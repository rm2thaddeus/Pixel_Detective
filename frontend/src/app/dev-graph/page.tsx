'use client';
_
import dynamic from 'next/dynamic';
import { Box, Heading, Spinner, Alert, AlertIcon, Text, HStack, Switch, Slider, SliderFilledTrack, SliderThumb, SliderTrack, useDisclosure, Button, useToast, Tabs, TabList, TabPanels, Tab, TabPanel } from '@chakra-ui/react';
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Header } from '@/components/Header';
import TimelineView from './components/TimelineView';
import EvolutionGraph from './components/EvolutionGraph';
import NodeDetailDrawer from './components/NodeDetailDrawer';
import SearchBar from './components/SearchBar';
import { SprintView, Sprint } from './components/SprintView';
import { TemporalAnalytics } from './components/TemporalAnalytics';

// Use the 2D-only bundle to avoid VR/A-Frame dependencies being pulled in
const ForceGraph2D = dynamic<any>(() => import('react-force-graph-2d'), { ssr: false });

// Developer Graph API base URL (configurable via env)
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

export default function DevGraphPage() {
	const nodesQuery = useQuery({
		queryKey: ['dev-graph', 'nodes'],
		queryFn: async () => {
			console.log('Fetching nodes from:', `${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes?limit=200`);
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes?limit=200`);
			if (!res.ok) throw new Error('Failed to load nodes');
			const data = await res.json();
			console.log('Nodes data:', data);
			return data;
		},
		staleTime: 5 * 60 * 1000,
	});

	const linksQuery = useQuery({
		queryKey: ['dev-graph', 'relations'],
		queryFn: async () => {
			console.log('Fetching relations from:', `${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations?limit=500`);
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations?limit=500`);
			if (!res.ok) throw new Error('Failed to load relations');
			const data = await res.json();
			console.log('Relations data:', data);
			return data;
		},
		staleTime: 5 * 60 * 1000,
	});

	const commitsQuery = useQuery({
		queryKey: ['dev-graph', 'commits'],
		queryFn: async () => {
			const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=${commitLimit}`);
			if (!res.ok) throw new Error('Failed to load commits');
			return res.json();
		},
		staleTime: 5 * 60 * 1000,
	});

	const [commitLimit, setCommitLimit] = useState(100);
	const [ingesting, setIngesting] = useState(false);
	const [selectedNode, setSelectedNode] = useState<any>(null);
	const [selectedRange, setSelectedRange] = useState<{ start?: string; end?: string }>({});
	const [subgraph, setSubgraph] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
	const [selectedSprint, setSelectedSprint] = useState<Sprint | undefined>();
	
	const drawer = useDisclosure();
	const toast = useToast();

	const fetchSubgraph = async (startCommit?: string, endCommit?: string) => {
		const params = new URLSearchParams();
		if (startCommit) params.set('start_commit', startCommit);
		if (endCommit) params.set('end_commit', endCommit);
		params.set('limit', '800');
		const url = `${DEV_GRAPH_API_URL}/api/v1/dev-graph/subgraph/by-commits?${params.toString()}`;
		const res = await fetch(url);
		if (!res.ok) throw new Error('Failed to load time-bounded subgraph');
		const sg = await res.json();
		setSubgraph(sg);
	};

	const data = useMemo(
		() => ({
			nodes: selectedRange.start || selectedRange.end ? (subgraph.nodes ?? []) : (nodesQuery.data ?? []),
			links: selectedRange.start || selectedRange.end ? (subgraph.links ?? []) : (linksQuery.data ?? []),
		}),
		[nodesQuery.data, linksQuery.data, selectedRange, subgraph]
	);

	const [showEvolves, setShowEvolves] = useState(true);

	const filteredData = useMemo(() => {
		const baseNodes = data.nodes ?? [];
		const baseLinks = data.links ?? [];
		return {
			nodes: baseNodes,
			links: baseLinks.filter((l: any) => showEvolves ? true : l.type !== 'EVOLVES_FROM'),
		};
	}, [data, showEvolves]);

	console.log('Graph data for rendering:', data);

	// Data validation
	const isValidData = (filteredData.nodes?.length ?? 0) > 0 && (filteredData.links?.length ?? 0) > 0;
	const hasValidLinks = (filteredData.links ?? []).every((link: any) => 
		link.from && link.to && link.type && 
		(filteredData.nodes ?? []).some((node: any) => node.id === link.from) &&
		(filteredData.nodes ?? []).some((node: any) => node.id === link.to)
	);

	return (
		<Box minH="100vh">
			<Header />
			<Box p={8}>
				<Heading mb={4}>Developer Graph</Heading>
				
				{/* Debug Info */}
				<Box mb={4} p={4} bg="gray.100" borderRadius="md" fontSize="sm">
					<Text fontWeight="bold">Debug Info:</Text>
					<Text>Nodes loaded: {nodesQuery.data?.length || 0}</Text>
					<Text>Links loaded: {linksQuery.data?.length || 0}</Text>
					<Text>Commits loaded: {Array.isArray(commitsQuery.data) ? commitsQuery.data.length : 0}</Text>
					<Text>Data valid: {isValidData ? 'Yes' : 'No'}</Text>
					<Text>Links valid: {hasValidLinks ? 'Yes' : 'No'}</Text>
					{!hasValidLinks && data.links.length > 0 && (
						<Text color="red">
							Invalid links: {data.links.filter((link: any) => 
								!link.from || !link.to || !link.type ||
								!data.nodes.some((node: any) => node.id === link.from) ||
								!data.nodes.some((node: any) => node.id === link.to)
							).length} found
						</Text>
					)}
				</Box>

				{/* Controls */}
				<HStack mb={3}>
					<HStack>
						<Switch isChecked={showEvolves} onChange={(e) => setShowEvolves(e.target.checked)} />
						<Text>Show EVOLVES_FROM</Text>
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
								linksQuery.refetch(),
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
							const links = (selectedRange.start || selectedRange.end ? subgraph.links : linksQuery.data) || [];
							const filteredLinks = links.filter((l: any) => nodeIds.has(l.from) || nodeIds.has(l.to));
							
							setSubgraph({ nodes, links: filteredLinks });
							setSelectedRange({});
							
							console.log(`Search results: ${nodes.length} nodes found with filters:`, filters);
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
							<Tab>Sprint View</Tab>
							<Tab>Analytics</Tab>
						</TabList>
						
						<TabPanels>
							{/* Timeline Tab */}
							<TabPanel>
								<TimelineView
									events={(Array.isArray(commitsQuery.data) ? commitsQuery.data : []).map((c: any) => ({
										id: c.hash,
										title: c.message,
										timestamp: c.timestamp,
										author: c.author_email,
										type: 'commit',
										commit_hash: c.hash,
										files_changed: c.files_changed,
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
										console.log('Time scrubbing to:', timestamp);
										// TODO: Implement graph filtering based on timestamp
										// This will be enhanced in the next iteration
									}}
								/>
							</TabPanel>
							
							{/* Sprint Tab */}
							<TabPanel>
								<SprintView
									sprints={[
										// Mock sprint data - replace with real API call
										{
											number: "1",
											start_date: "2024-01-01",
											end_date: "2024-01-14",
											commit_range: {
												start: "abc123",
												end: "def456"
											},
											metrics: {
												total_commits: 45,
												files_changed: 23,
												requirements_implemented: 8,
												authors: 3
											}
										},
										{
											number: "2",
											start_date: "2024-01-15",
											end_date: "2024-01-28",
											commit_range: {
												start: "def456",
												end: "ghi789"
											},
											metrics: {
												total_commits: 52,
												files_changed: 31,
												requirements_implemented: 12,
												authors: 4
											}
										}
									]}
									onSprintSelect={(sprint) => {
										setSelectedSprint(sprint);
										// Fetch subgraph for sprint commit range
										fetchSubgraph(sprint.commit_range.start, sprint.commit_range.end).catch(console.error);
									}}
									selectedSprint={selectedSprint}
								/>
							</TabPanel>
							
							{/* Analytics Tab */}
							<TabPanel>
								<TemporalAnalytics
									events={(Array.isArray(commitsQuery.data) ? commitsQuery.data : []).map((c: any) => ({
										id: c.hash,
										timestamp: c.timestamp,
										type: c.type || 'commit',
										author: c.author_email,
										files_changed: c.files_changed,
									}))}
									nodes={nodesQuery.data || []}
									links={linksQuery.data || []}
								/>
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
					<Text><span style={{ color: '#888' }}>■</span> PART_OF</Text>
					<Text><span style={{ color: '#2b8a3e' }}>■</span> EVOLVES_FROM</Text>
					<Text><span style={{ color: '#1c7ed6' }}>■</span> REFERENCES</Text>
					<Text><span style={{ color: '#e67700' }}>■</span> DEPENDS_ON</Text>
				</Box>

				{(nodesQuery.isLoading || linksQuery.isLoading) && (
					<Box display="flex" alignItems="center" gap={2} mb={4}>
						<Spinner size="sm" />
						Loading graph...
					</Box>
				)}
				
				{(nodesQuery.error || linksQuery.error) && (
					<Alert status="error" mb={4}>
						<AlertIcon />
						{(nodesQuery.error as Error)?.message || (linksQuery.error as Error)?.message || 'Failed to load graph'}
					</Alert>
				)}
				
				{isValidData && hasValidLinks && (
					<EvolutionGraph 
						data={filteredData}
						onNodeClick={(n: any) => { setSelectedNode(n); drawer.onOpen(); }}
						currentTimestamp={selectedRange.start ? commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp : undefined}
						timeRange={selectedRange.start && selectedRange.end ? {
							start: commitsQuery.data?.find((c: any) => c.hash === selectedRange.start)?.timestamp || '',
							end: commitsQuery.data?.find((c: any) => c.hash === selectedRange.end)?.timestamp || ''
						} : undefined}
					/>
				)}
				
				{!isValidData && !nodesQuery.isLoading && (
					<Alert status="info">
						<AlertIcon />
						No graph data available. Please check if the Developer Graph API is running.
					</Alert>
				)}
				
				{isValidData && !hasValidLinks && (
					<Alert status="warning">
						<AlertIcon />
						Graph data loaded but some links reference non-existent nodes. Check the debug info above.
					</Alert>
				)}
			</Box>
			<NodeDetailDrawer isOpen={drawer.isOpen} onClose={drawer.onClose} node={selectedNode} />
		</Box>
	);
}
