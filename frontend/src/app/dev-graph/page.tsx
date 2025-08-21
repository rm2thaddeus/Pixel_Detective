'use client';

import dynamic from 'next/dynamic';
import { Box, Heading, Spinner, Alert, AlertIcon, Text, HStack, Switch } from '@chakra-ui/react';
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Header } from '@/components/Header';

// Use the 2D-only bundle to avoid VR/A-Frame dependencies being pulled in
const ForceGraph2D = dynamic<any>(() => import('react-force-graph-2d'), { ssr: false });

// Developer Graph API runs on port 8080
const DEV_GRAPH_API_URL = 'http://localhost:8080';

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

	const data = useMemo(
		() => ({
			nodes: nodesQuery.data ?? [],
			links: linksQuery.data ?? [],
		}),
		[nodesQuery.data, linksQuery.data]
	);

	console.log('Graph data for rendering:', data);

	// Data validation
	const isValidData = data.nodes.length > 0 && data.links.length > 0;
	const hasValidLinks = data.links.every((link: any) => 
		link.from && link.to && link.type && 
		data.nodes.some((node: any) => node.id === link.from) &&
		data.nodes.some((node: any) => node.id === link.to)
	);

	const [showEvolves, setShowEvolves] = useState(true);

	const filteredData = useMemo(() => {
		if (!nodesQuery.data || !linksQuery.data) return data;
		return {
			nodes: nodesQuery.data,
			links: linksQuery.data.filter((l: any) => showEvolves ? true : l.type !== 'EVOLVES_FROM'),
		};
	}, [nodesQuery.data, linksQuery.data, showEvolves]);

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
				</HStack>

				{/* Legend */}
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
					<ForceGraph2D 
						graphData={filteredData} 
						height={600} 
						width={1000}
						nodeLabel={(n: any) => `${n.id}\n${n.type ?? ''}`}
						linkLabel={(l: any) => l.type}
						nodeAutoColorBy={(n: any) => n.type ?? 'Unknown'}
						linkColor={(l: any) => (
							l.type === 'PART_OF' ? '#888' :
							l.type === 'EVOLVES_FROM' ? '#2b8a3e' :
							l.type === 'REFERENCES' ? '#1c7ed6' :
							l.type === 'DEPENDS_ON' ? '#e67700' : '#999'
						)}
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
		</Box>
	);
}
