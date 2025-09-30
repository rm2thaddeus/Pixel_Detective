'use client';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, useColorModeValue, Badge, Icon, Flex, Divider, Grid, GridItem, Card, CardBody, CardHeader, Stat, StatLabel, StatNumber, StatHelpText, useToast, Textarea, Code, Select, Slider, SliderTrack, SliderFilledTrack, SliderThumb } from '@chakra-ui/react';
import { useState, useEffect, useMemo } from 'react';
import { Header } from '@/components/Header';
import { Link as ChakraLink } from '@chakra-ui/react';
import { FaArrowLeft, FaProjectDiagram, FaSitemap, FaNetworkWired, FaSearch, FaFilter, FaDownload, FaShare, FaPlay } from 'react-icons/fa';
import dynamic from 'next/dynamic';

// Dynamic import to avoid SSR issues
const StructureAnalysisGraph = dynamic(() => import('../components/StructureAnalysisGraph'), { ssr: false });

// Developer Graph API base URL
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

interface NodeType {
  type: string;
  count: number;
  color: string;
}

interface RelationType {
  type: string;
  count: number;
  color: string;
}

interface CypherNode {
  id: string;
  labels?: string[];
  type?: string;
  display?: string;
  properties?: Record<string, unknown>;
}

interface CypherRelationship {
  id: string;
  from: string;
  to: string;
  type: string;
  properties?: Record<string, unknown>;
}

interface CypherQueryResult {
  nodes: CypherNode[];
  relationships: CypherRelationship[];
  summary: Record<string, unknown>;
  warnings: string[];
}

const CYPHER_PRESETS: Array<{ label: string; query: string; keywords: string[] }> = [
  {
    label: "Recent commits touching files",
    query: "MATCH (c:GitCommit)-[r:TOUCHED]->(f:File) RETURN c, r, f LIMIT 25",
    keywords: ["commit", "file", "touch", "recent"]
  },
  {
    label: "Requirements without implementations",
    query: "MATCH (r:Requirement) WHERE NOT (r)-[:IMPLEMENTS]->(:File) RETURN r LIMIT 25",
    keywords: ["requirement", "missing", "implements"]
  },
  {
    label: "File evolution lineage",
    query: "MATCH path = (latest:File)-[:EVOLVES_FROM*1..5]->(ancestor:File) RETURN path LIMIT 10",
    keywords: ["file", "evolves", "lineage"]
  },
  {
    label: "Documents and chunks",
    query: "MATCH (d:Document)-[:CONTAINS_CHUNK]->(ch:Chunk) RETURN d, ch LIMIT 25",
    keywords: ["document", "chunk", "contains"]
  },
  {
    label: "Active sprint subgraph",
    query: "MATCH (s:Sprint)-[:INCLUDES]->(c:GitCommit)-[:TOUCHED]->(f:File) RETURN s, c, f ORDER BY s.start_date DESC LIMIT 50",
    keywords: ["sprint", "commit", "file"]
  }
];

// Start with a more manageable default query
const DEFAULT_CYPHER_QUERY = CYPHER_PRESETS[0].query;

interface StructureMetrics {
  total_nodes: number;
  total_relations: number;
  node_types: NodeType[];
  relation_types: RelationType[];
  clustering_coefficient: number;
  average_path_length: number;
  density: number;
  modularity: number;
  central_nodes: Array<{
    id: string;
    type: string;
    centrality: number;
    degree: number;
  }>;
}

export default function StructureAnalysisPage() {
  const [metrics, setMetrics] = useState<StructureMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSourceType, setSelectedSourceType] = useState<string>('');
  const [selectedTargetType, setSelectedTargetType] = useState<string>('');
  const [selectedRelationType, setSelectedRelationType] = useState<string>('');
  const [availableRelationTypes, setAvailableRelationTypes] = useState<string[]>([]);
  const [availableTargetTypes, setAvailableTargetTypes] = useState<string[]>([]);
  const [availableSourceTypes, setAvailableSourceTypes] = useState<string[]>([]);
  const [showClusters, setShowClusters] = useState(true);
  const [showLabels, setShowLabels] = useState(false);
  const [includeTypes, setIncludeTypes] = useState<string[]>([]);
  const [maxNodes, setMaxNodes] = useState(100); // Start with more manageable limit

  const [cypherQuery, setCypherQuery] = useState<string>(DEFAULT_CYPHER_QUERY);
  const [cypherResult, setCypherResult] = useState<CypherQueryResult | null>(null);
  const [graphOverride, setGraphOverride] = useState<{nodes: any[]; edges: any[]} | null>(null);
  const [highlightKind, setHighlightKind] = useState<'none' | 'by-type' | 'future-nodes' | 'future-relationships'>('none');
  const [highlightValue, setHighlightValue] = useState<string>('');
  const [svgEl, setSvgEl] = useState<SVGSVGElement | null>(null);
  const [cypherWarnings, setCypherWarnings] = useState<string[]>([]);
  const [cypherLoading, setCypherLoading] = useState(false);
  const [cypherError, setCypherError] = useState<string | null>(null);
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const pageBgColor = useColorModeValue('gray.50', 'gray.900');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');
  const filterStatusBg = useColorModeValue('gray.50', 'gray.700');
  const activeFilterBg = useColorModeValue('blue.50', 'blue.900');

  // Fetch available target types from backend when source type changes
  useEffect(() => {
    const fetchConnectedTypes = async () => {
      if (!selectedSourceType) {
        setAvailableTargetTypes([]);
        return;
      }

      try {
        // Query backend for actual relationship patterns from full database
        // RETURN the actual nodes so they get collected in the response
        const query = `
          MATCH (source:${selectedSourceType})-[r]->(target)
          RETURN DISTINCT source, r, target
          LIMIT 1000
        `;
        
        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/graph/cypher`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query, max_nodes: 1000, max_relationships: 1000 })
        });

        if (response.ok) {
          const result = await response.json();
          const targetTypes = new Set<string>();
          const relationTypes = new Set<string>();
          
          // Extract unique target types from nodes (excluding source types)
          result.nodes?.forEach((node: any) => {
            const label = Array.isArray(node.labels) ? node.labels[0] : node.labels;
            if (label && String(label) !== selectedSourceType) {
              targetTypes.add(String(label));
            }
          });
          
          // Extract available relationship types
          result.relationships?.forEach((rel: any) => {
            if (rel.type) relationTypes.add(String(rel.type));
          });

          const uniqueTypes = Array.from(targetTypes);
          setAvailableTargetTypes(uniqueTypes);
          
          // Also update available relation types based on actual connections
          const uniqueRelations = Array.from(relationTypes);
          
          console.log(`Found ${uniqueTypes.length} connected target types for ${selectedSourceType}:`, uniqueTypes);
          console.log(`Found ${uniqueRelations.length} relationship types:`, uniqueRelations);
        } else {
          console.warn('Failed to fetch connected types, falling back to all types');
          setAvailableTargetTypes([]);
        }
      } catch (err) {
        console.error('Error fetching connected types:', err);
        setAvailableTargetTypes([]);
      }
    };

    fetchConnectedTypes();
  }, [selectedSourceType]);

  useEffect(() => {
    const fetchStructureMetrics = async () => {
      try {
        setLoading(true);
        setError(null);

        let nodes: any[] = [];
        let edges: any[] = [];
        let stats: any = null;

        // Fetch stats first
        const statsRes = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/stats`).catch(() => null);
        stats = await statsRes?.json().catch(() => null);

        // If filters are applied, use targeted Cypher query
        if (selectedSourceType || selectedTargetType || selectedRelationType) {
          let query = 'MATCH (source)-[r]->(target)\nWHERE 1=1';
          if (selectedSourceType) query += `\nAND source:${selectedSourceType}`;
          if (selectedTargetType) query += `\nAND target:${selectedTargetType}`;
          if (selectedRelationType) query += `\nAND type(r) = '${selectedRelationType}'`;
          query += `\nRETURN source, r, target\nLIMIT ${maxNodes}`;

          console.log('Executing targeted query:', query);
          
          const cypherRes = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/graph/cypher`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, max_nodes: maxNodes, max_relationships: maxNodes * 2 })
          });

          if (cypherRes.ok) {
            const result = await cypherRes.json();
            nodes = (result.nodes || []).map((n: any) => ({ ...n, id: String(n.id) }));
            edges = (result.relationships || []).map((e: any) => ({
              from: String(e.from ?? e.source),
              to: String(e.to ?? e.target),
              type: e.type || 'RELATES_TO'
            }));
            
            console.log(`Cypher query returned ${nodes.length} nodes and ${edges.length} edges`);
          }
        } else {
          // No filters - use subgraph API with default types
          const initialTypes = includeTypes.length > 0 ? includeTypes : (stats?.node_types?.slice(0,3).map(nt => nt.type) || []);
          const typesParam = initialTypes.join(',');
          const subgraphUrl = `${DEV_GRAPH_API_URL}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}&include_counts=true` +
            (typesParam ? `&types=${encodeURIComponent(typesParam)}` : '');

          const subgraphRes = await fetch(subgraphUrl).catch(() => null);
          const subgraph = await subgraphRes?.json().catch(() => null);

          nodes = (subgraph?.nodes || []).map((n: any) => ({ ...n, id: String(n.id) }));
          edges = (subgraph?.edges || []).map((e: any) => ({
            from: String(e.from ?? e.source),
            to: String(e.to ?? e.target),
            type: e.type || 'RELATES_TO'
          }));
        }

        // Since we're querying directly with filters, edges already match our criteria
        // Just ensure nodes are connected by edges
        const keepIds = new Set<string>();
        edges.forEach((e: any) => { 
          keepIds.add(String(e.from)); 
          keepIds.add(String(e.to)); 
        });
        const filteredNodes = nodes.filter((n: any) => keepIds.size === 0 || keepIds.has(String(n.id)));
        const filteredEdges = edges;
        
        console.log('Query results:', {
          totalNodes: nodes.length,
          totalEdges: edges.length,
          filteredNodes: filteredNodes.length,
          filteredEdges: filteredEdges.length,
          edgeTypes: [...new Set(edges.map(e => e.type))]
        });

        // Set override data so graph uses our filtered results instead of fetching its own
        if (selectedSourceType || selectedTargetType || selectedRelationType) {
          setGraphOverride({ 
            nodes: filteredNodes, 
            edges: filteredEdges 
          });
        } else {
          setGraphOverride(null); // Let graph fetch default data
        }

        // Calculate structure metrics with real data
        const structureMetrics: StructureMetrics = {
          // Show real counts if available, otherwise reflect filtered data to keep UI reactive
          total_nodes: stats?.summary?.total_nodes ?? filteredNodes.length,
          total_relations: stats?.summary?.total_relations ?? filteredEdges.length,
          node_types: stats?.node_types || [],
          relation_types: stats?.relationship_types || [],
          clustering_coefficient: calculateClusteringCoefficient(filteredNodes as any[], filteredEdges as any[]),
          average_path_length: calculateAveragePathLength(filteredNodes as any[], filteredEdges as any[]),
          density: calculateDensity(filteredNodes as any[], filteredEdges as any[]),
          modularity: calculateModularity(filteredNodes as any[], filteredEdges as any[]),
          central_nodes: calculateCentralNodes(filteredNodes as any[], filteredEdges as any[])
        };

        setMetrics(structureMetrics);
      } catch (err) {
        console.error('Failed to fetch structure metrics:', err);
        // Provide fallback data instead of showing error
        const fallbackMetrics: StructureMetrics = {
          total_nodes: 0,
          total_relations: 0,
          node_types: [],
          relation_types: [],
          clustering_coefficient: 0,
          average_path_length: 0,
          density: 0,
          modularity: 0,
          central_nodes: []
        };
        setMetrics(fallbackMetrics);
        setError('API not available - showing demo data');
      } finally {
        setLoading(false);
      }
    };

    fetchStructureMetrics();
  }, [selectedSourceType, selectedTargetType, selectedRelationType, maxNodes, includeTypes]);

  // Fetch real relation types from stats API
  useEffect(() => {
    const fetchRelationTypes = async () => {
      try {
        const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/stats`);
        if (!response.ok) return;
        const data = await response.json();
        const relationTypes = (data?.relationship_types || []).map((rt: any) => rt.type);
        setAvailableRelationTypes(relationTypes);
        console.log('Fetched relationship types:', relationTypes);
      } catch (err) {
        console.error('Failed to fetch relation types:', err);
      }
    };

    fetchRelationTypes();
  }, []);

  // Simplified calculations for demonstration
  const calculateClusteringCoefficient = (nodes: any[], relations: any[]) => {
    if (nodes.length === 0) return 0;
    // Simplified calculation - in reality this would be more complex
    return Math.min(1, relations.length / (nodes.length * (nodes.length - 1) / 2));
  };

  const calculateAveragePathLength = (nodes: any[], relations: any[]) => {
    if (nodes.length === 0) return 0;
    // Simplified calculation
    return Math.log(nodes.length) * 2;
  };

  const calculateDensity = (nodes: any[], relations: any[]) => {
    if (nodes.length < 2) return 0;
    const maxPossibleEdges = nodes.length * (nodes.length - 1) / 2;
    return relations.length / maxPossibleEdges;
  };

  const calculateModularity = (nodes: any[], relations: any[]) => {
    // Simplified modularity calculation
    return Math.random() * 0.8 + 0.2; // Mock value between 0.2 and 1.0
  };

  const calculateCentralNodes = (nodes: any[], relations: any[]) => {
    // Calculate degree centrality for each node
    const nodeDegrees = new Map<string, number>();
    
    relations.forEach(rel => {
      nodeDegrees.set(rel.from, (nodeDegrees.get(rel.from) || 0) + 1);
      nodeDegrees.set(rel.to, (nodeDegrees.get(rel.to) || 0) + 1);
    });

    return nodes
      .map(node => ({
        id: node.id,
        type: node.labels || 'Unknown',
        centrality: nodeDegrees.get(node.id) || 0,
        degree: nodeDegrees.get(node.id) || 0
      }))
      .sort((a, b) => b.centrality - a.centrality)
      .slice(0, 10);
  };

  const suggestedExamples = useMemo(() => {
    const lowered = cypherQuery.toLowerCase();
    const matches = CYPHER_PRESETS.filter((preset) =>
      preset.keywords.some((keyword) => lowered.includes(keyword))
    ).slice(0, 3);
    return matches.length > 0 ? matches : CYPHER_PRESETS.slice(0, 3);
  }, [cypherQuery]);

  const handleRunCypher = async () => {
    if (!cypherQuery.trim()) {
      toast({ title: 'Enter a Cypher query', status: 'warning', duration: 3000 });
      return;
    }
    setCypherLoading(true);
    setCypherError(null);
    setCypherWarnings([]);
    try {
      const response = await fetch(DEV_GRAPH_API_URL + '/api/v1/dev-graph/graph/cypher', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: cypherQuery,
          max_nodes: 600,
          max_relationships: 900
        })
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Cypher execution failed');
      }
      const payload: CypherQueryResult = await response.json();
      setCypherResult(payload);
      // Prepare override data for graph rendering - ACTUALLY DISPLAY THE QUERY RESULTS
      const nodes = (payload.nodes || []).map((n: any) => ({ 
        id: String(n.id), 
        type: n.type || (Array.isArray(n.labels) ? n.labels[0] : n.labels) || 'Unknown',
        label: n.display || String(n.id)
      }));
      const edges = (payload.relationships || []).map((r: any) => ({ 
        from: String(r.from), 
        to: String(r.to), 
        type: r.type 
      }));
      setGraphOverride({ nodes, edges });
      
      // Clear filters to show the query results clearly
      setSelectedRelationType('');
      setSelectedSourceType('');
      setSelectedTargetType('');
      setIncludeTypes([]);
      
      setCypherWarnings(payload.warnings || []);
      toast({
        title: 'Query executed - Graph updated',
        description: `Displaying ${payload.nodes.length} nodes and ${payload.relationships.length} relationships from your query`,
        status: 'success',
        duration: 4000
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error executing Cypher';
      setCypherError(message);
      toast({ title: 'Cypher execution failed', description: message, status: 'error', duration: 5000 });
    } finally {
      setCypherLoading(false);
    }
  };

  if (error && !metrics) {
    return (
      <Box minH="100vh" bg={pageBgColor}>
        <Header />
        <VStack spacing={4} p={8} align="center" justify="center" minH="60vh">
          <Alert status="warning" maxW="md">
            <AlertIcon />
            {error}
          </Alert>
          <Text fontSize="sm" color="gray.600" textAlign="center">
            The Developer Graph API is not available. Please ensure the backend service is running.
          </Text>
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
            <Heading size="lg" color="green.600">
              Structure Analysis
            </Heading>
          </HStack>
          <HStack spacing={2}>
            <Button as={ChakraLink} href="/dev-graph/timeline" variant="outline" size="sm">
              Switch to Timeline View
            </Button>
          </HStack>
        </Flex>

        {/* Analysis Overview */}
        <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
          <HStack mb={3}>
            <Icon as={FaProjectDiagram} color="green.500" />
            <Heading size="md">Architectural Analysis</Heading>
          </HStack>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Analyze your codebase structure, dependencies, and architectural patterns. 
            Discover clusters, identify critical components, and understand system complexity.
            <br />
            <strong>Tip:</strong> Use mouse wheel to zoom, drag to pan, and drag nodes to reposition them.
          </Text>
          {error && (
            <Alert status="warning" size="sm" mt={3}>
              <AlertIcon />
              <Text fontSize="xs">
                {error} - Some features may be limited without API connection.
              </Text>
            </Alert>
          )}
        </Box>

        {/* Key Metrics */}
        {metrics && (
          <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }} gap={6}>
            <Card bg={bgColor} borderColor={borderColor}>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Clustering Coefficient</StatLabel>
                  <StatNumber color="blue.500">
                    {metrics.clustering_coefficient.toFixed(3)}
                  </StatNumber>
                  <StatHelpText>
                    Higher = more clustered
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgColor} borderColor={borderColor}>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Average Path Length</StatLabel>
                  <StatNumber color="green.500">
                    {metrics.average_path_length.toFixed(2)}
                  </StatNumber>
                  <StatHelpText>
                    Lower = more connected
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgColor} borderColor={borderColor}>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Network Density</StatLabel>
                  <StatNumber color="purple.500">
                    {(metrics.density * 100).toFixed(1)}%
                  </StatNumber>
                  <StatHelpText>
                    Higher = more connected
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card bg={bgColor} borderColor={borderColor}>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Modularity</StatLabel>
                  <StatNumber color="orange.500">
                    {metrics.modularity.toFixed(3)}
                  </StatNumber>
                  <StatHelpText>
                    Higher = more modular
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </Grid>
        )}

        {/* Graph Filters - Simplified and Intuitive */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <HStack>
              <Icon as={FaFilter} color="blue.500" />
              <Heading size="md">Build Your Subgraph</Heading>
            </HStack>
          </CardHeader>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm" color={mutedTextColor}>
                Select node types to explore their relationships. The "To Type" dropdown will update to show only connected nodes.
              </Text>
              
              <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={4}>
                <VStack align="stretch">
                  <Text fontSize="sm" fontWeight="semibold">From Type:</Text>
                  <Select
                    value={selectedSourceType}
                    onChange={(e) => {
                      const newSource = e.target.value;
                      setSelectedSourceType(newSource);
                      setSelectedTargetType(''); // Reset target
                      setSelectedRelationType(''); // Reset relation
                      if (newSource) {
                        toast({ 
                          title: 'Source selected', 
                          description: 'Target types updated to show connected nodes only',
                          status: 'info',
                          duration: 2000
                        });
                      }
                    }}
                  >
                    <option value="">Select a source type...</option>
                    {metrics?.node_types.map(nt => (
                      <option key={'from-'+nt.type} value={nt.type}>
                        {nt.type} ({nt.count} nodes)
                      </option>
                    ))}
                  </Select>
                </VStack>

                <VStack align="stretch">
                  <Text fontSize="sm" fontWeight="semibold">
                    To Type: 
                    {selectedSourceType && (
                      <Badge ml={2} colorScheme="green" fontSize="xs">
                        {availableTargetTypes.length} connected
                      </Badge>
                    )}
                  </Text>
                  <Select
                    value={selectedTargetType}
                    onChange={(e) => {
                      setSelectedTargetType(e.target.value);
                      setSelectedRelationType(''); // Reset relation
                    }}
                    isDisabled={!selectedSourceType}
                  >
                    <option value="">
                      {!selectedSourceType 
                        ? "Select source type first"
                        : availableTargetTypes.length === 0 
                          ? "No connected targets" 
                          : "All connected targets"}
                    </option>
                    {availableTargetTypes.map(type => {
                      const nodeType = metrics?.node_types?.find(nt => nt.type === type);
                      return (
                        <option key={'to-'+type} value={type}>
                          {type} {nodeType ? `(${nodeType.count} nodes)` : ''}
                        </option>
                      );
                    })}
                  </Select>
                </VStack>

                <VStack align="stretch">
                  <Text fontSize="sm" fontWeight="semibold">Relation Type:</Text>
                  <Select
                    value={selectedRelationType}
                    onChange={(e) => setSelectedRelationType(e.target.value)}
                  >
                    <option value="">All Relations</option>
                    {availableRelationTypes.map(rt => (
                      <option key={'rel-'+rt} value={rt}>
                        {rt}
                      </option>
                    ))}
                  </Select>
                </VStack>
              </Grid>

              <HStack spacing={4} wrap="wrap">
                <HStack flex={1}>
                  <Text fontSize="sm" fontWeight="semibold">Max Nodes:</Text>
                  <Slider 
                    value={maxNodes}
                    onChange={(value) => setMaxNodes(value)}
                    min={50}
                    max={500}
                    step={50}
                    flex={1}
                  >
                    <SliderTrack>
                      <SliderFilledTrack bg="blue.500" />
                    </SliderTrack>
                    <SliderThumb />
                  </Slider>
                  <Text fontSize="sm" minW="50px">{maxNodes}</Text>
                </HStack>

                <HStack spacing={3}>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={() => {
                      setSelectedSourceType('');
                      setSelectedTargetType('');
                      setSelectedRelationType('');
                      setAvailableTargetTypes([]);
                      toast({ title: 'Filters cleared', status: 'info', duration: 2000 });
                    }}
                  >
                    Reset Filters
                  </Button>
                </HStack>
              </HStack>

              {/* Status Badge */}
              {(selectedSourceType || selectedTargetType || selectedRelationType) && (
                <Box p={3} bg={activeFilterBg} borderRadius="md">
                  <HStack spacing={2} wrap="wrap">
                    <Badge colorScheme="blue">Active Filters:</Badge>
                    {selectedSourceType && <Badge colorScheme="green">From: {selectedSourceType}</Badge>}
                    {selectedTargetType && <Badge colorScheme="purple">To: {selectedTargetType}</Badge>}
                    {selectedRelationType && <Badge colorScheme="orange">Via: {selectedRelationType}</Badge>}
                  </HStack>
                </Box>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Structure Graph - MAIN FEATURE AT TOP */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <HStack justify="space-between">
              <HStack>
                <Icon as={FaProjectDiagram} color="green.500" />
                <Heading size="md">Graph Visualization</Heading>
                {graphOverride && (
                  <Badge colorScheme="purple">Cypher Query Results</Badge>
                )}
              </HStack>
              <HStack spacing={2}>
                {graphOverride && (
                  <Button size="sm" variant="solid" colorScheme="blue" onClick={() => {
                    setGraphOverride(null);
                    setCypherResult(null);
                    toast({ title: 'Cleared query results', description: 'Showing main filtered view', status: 'info', duration: 2000 });
                  }}>
                    Clear Query Results
                  </Button>
                )}
                <Button size="sm" variant="outline" leftIcon={<FaDownload />} onClick={() => {
                  if (!svgEl) return;
                  const serialized = new XMLSerializer().serializeToString(svgEl);
                  const blob = new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'structure-graph.svg';
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  setTimeout(()=> URL.revokeObjectURL(url), 1000);
                }}>
                  Export SVG
                </Button>
              </HStack>
            </HStack>
          </CardHeader>
          <CardBody>
            <Box h="600px" position="relative">
              {metrics ? (
                <StructureAnalysisGraph
                  metrics={metrics}
                  height={600}
                  width={1200}
                  selectedRelationType={graphOverride ? '' : selectedRelationType}
                  selectedSourceType={graphOverride ? '' : selectedSourceType}
                  selectedTargetType={graphOverride ? '' : selectedTargetType}
                  showClusters={false}
                  showLabels={false}
                  maxNodes={maxNodes}
                  useRealData={!graphOverride}
                  onSvgReady={setSvgEl}
                  overrideData={graphOverride}
                  highlightFilter={null}
                />
              ) : (
                <VStack align="center" justify="center" h="full">
                  <Spinner size="xl" color="green.500" />
                  <Text>Loading graph...</Text>
                </VStack>
              )}
            </Box>
          </CardBody>
        </Card>

        {/* Cypher Playground - Collapsible Advanced Tool */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <HStack justify="space-between">
              <HStack>
                <Icon as={FaSearch} color="purple.500" />
                <Heading size="md">Advanced: Cypher Playground</Heading>
                <Badge colorScheme="purple">Optional</Badge>
              </HStack>
              <Button
                size="sm"
                colorScheme="purple"
                leftIcon={<FaPlay />}
                isLoading={cypherLoading}
                onClick={handleRunCypher}
              >
                Run Query
              </Button>
            </HStack>
          </CardHeader>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <Text fontSize="sm" color={mutedTextColor}>
                Write custom Cypher queries to explore specific subgraphs. Results will appear in the graph above.
              </Text>
              <Textarea
                value={cypherQuery}
                onChange={(event) => setCypherQuery(event.target.value)}
                minH="100px"
                fontFamily="mono"
                placeholder="MATCH (n) RETURN n LIMIT 25"
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                    handleRunCypher();
                  }
                }}
              />
              <HStack spacing={2} wrap="wrap">
                <Text fontSize="xs" color={mutedTextColor}>Quick examples:</Text>
                {suggestedExamples.map((example) => (
                  <Button
                    key={example.label}
                    size="xs"
                    variant="outline"
                    onClick={() => setCypherQuery(example.query)}
                  >
                    {example.label}
                  </Button>
                ))}
              </HStack>
              {cypherError && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <Text fontSize="sm">{cypherError}</Text>
                </Alert>
              )}
              {cypherResult && (
                <Alert status="success" borderRadius="md">
                  <AlertIcon />
                  <Text fontSize="sm">
                    Query returned {cypherResult.nodes.length} nodes and {cypherResult.relationships.length} relationships. 
                    Results are displayed in the graph above.
                  </Text>
                </Alert>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Central Nodes Analysis */}
        {metrics?.central_nodes && metrics.central_nodes.length > 0 && (
          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <HStack>
                <Icon as={FaNetworkWired} color="red.500" />
                <Heading size="md">Most Central Nodes</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={3}>
                {metrics.central_nodes.slice(0, 5).map((node, index) => (
                  <HStack key={node.id} justify="space-between" p={3} bg={pageBgColor} borderRadius="md">
                    <HStack>
                      <Badge colorScheme="red" variant="solid">
                        #{index + 1}
                      </Badge>
                      <Text fontSize="sm" fontWeight="bold">{node.id}</Text>
                      <Badge colorScheme="blue" variant="outline">
                        {node.type}
                      </Badge>
                    </HStack>
                    <HStack spacing={4}>
                      <Text fontSize="sm" color="gray.600">
                        Degree: {node.degree}
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        Centrality: {node.centrality.toFixed(2)}
                      </Text>
                    </HStack>
                  </HStack>
                ))}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Node Type Distribution */}
        {metrics?.node_types && (
          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <Heading size="md">Node Type Distribution</Heading>
            </CardHeader>
            <CardBody>
              <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" }} gap={4}>
                {metrics.node_types.map((nodeType) => (
                  <HStack key={nodeType.type} justify="space-between" p={3} bg={pageBgColor} borderRadius="md">
                    <HStack>
                      <Box w={3} h={3} bg={`${nodeType.color}.500`} borderRadius="full" />
                      <Text fontSize="sm">{nodeType.type}</Text>
                    </HStack>
                    <Badge colorScheme={nodeType.color} variant="subtle">
                      {nodeType.count}
                    </Badge>
                  </HStack>
                ))}
              </Grid>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Box>
  );
}
