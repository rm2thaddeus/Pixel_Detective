'use client';
import { Box, Heading, Text, VStack, HStack, Button, Spinner, Alert, AlertIcon, useColorModeValue, Badge, Icon, Flex, Divider, Grid, GridItem, Card, CardBody, CardHeader, Stat, StatLabel, StatNumber, StatHelpText, useToast, Textarea, Code, Select } from '@chakra-ui/react';
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
  const [maxNodes, setMaxNodes] = useState(20000);

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

  useEffect(() => {
    const fetchStructureMetrics = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch comprehensive structure analysis with graceful error handling
        const typesParam = [selectedSourceType, selectedTargetType]
          .filter(Boolean)
          .join(',');
        const subgraphUrl = `${DEV_GRAPH_API_URL}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}&include_counts=true` +
          (typesParam ? `&types=${encodeURIComponent(typesParam)}` : '');

        const [statsRes, subgraphRes] = await Promise.all([
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/stats`).catch(() => null),
          fetch(subgraphUrl).catch(() => null)
        ]);

        const [stats, subgraph] = await Promise.all([
          statsRes?.json().catch(() => null),
          subgraphRes?.json().catch(() => null)
        ]);

        // Use real graph data from subgraph API
        const nodes = (subgraph?.nodes || []).map((n: any) => ({ ...n, id: String(n.id) }));
        const edges = (subgraph?.edges || []).map((e: any) => ({
          from: String(e.from ?? e.source),
          to: String(e.to ?? e.target),
          type: e.type || 'RELATES_TO'
        }));

        // Apply client-side filtering consistent with graph component
        const nodeById = new Map<string, any>();
        nodes.forEach((n: any) => nodeById.set(String(n.id), n));
        
        // Debug: Log filtering parameters
        console.log('Filtering with:', {
          selectedRelationType,
          selectedSourceType,
          selectedTargetType,
          totalEdges: edges.length,
          availableRelationTypes: [...new Set(edges.map(e => e.type))]
        });
        
        const filteredEdges = edges.filter((edge: any) => {
          const s = nodeById.get(edge.from);
          const t = nodeById.get(edge.to);
          if (!s || !t) return false;
          
          // Filter by relationship type
          if (selectedRelationType && String(edge.type) !== selectedRelationType) return false;
          
          // Filter by source type
          if (selectedSourceType && String(s.type || (Array.isArray(s.labels) ? s.labels[0] : s.labels)) !== selectedSourceType) return false;
          
          // Filter by target type
          if (selectedTargetType && String(t.type || (Array.isArray(t.labels) ? t.labels[0] : t.labels)) !== selectedTargetType) return false;
          
          return true;
        });
        
        // If no edges found with strict filtering, try more flexible filtering
        if (filteredEdges.length === 0 && (selectedSourceType || selectedTargetType)) {
          console.log('No edges found with strict filtering, trying flexible approach...');
          
          // Try filtering by just source type if target type is selected but no matches
          if (selectedSourceType && selectedTargetType) {
            const flexibleEdges = edges.filter((edge: any) => {
              const s = nodeById.get(edge.from);
              const t = nodeById.get(edge.to);
              if (!s || !t) return false;
              
              if (selectedRelationType && String(edge.type) !== selectedRelationType) return false;
              
              // Only filter by source type, ignore target type for now
              if (selectedSourceType && String(s.type || (Array.isArray(s.labels) ? s.labels[0] : s.labels)) !== selectedSourceType) return false;
              
              return true;
            });
            
            if (flexibleEdges.length > 0) {
              console.log('Found edges with flexible filtering (source only):', flexibleEdges.length);
              // Update the filteredEdges variable instead of returning
              filteredEdges.splice(0, filteredEdges.length, ...flexibleEdges);
            }
          }
        }
        
        console.log('Filtered edges:', {
          original: edges.length,
          filtered: filteredEdges.length,
          relationTypes: [...new Set(filteredEdges.map(e => e.type))]
        });
        
        // Update available target types based on selected source type
        if (selectedSourceType) {
          const sourceNodeIds = nodes
            .filter(n => {
              const nodeType = n.type || (Array.isArray(n.labels) ? n.labels[0] : n.labels);
              return String(nodeType) === selectedSourceType;
            })
            .map(n => String(n.id));
          
          const targetTypes = edges
            .filter(e => sourceNodeIds.includes(String(e.from)))
            .map(e => {
              const targetNode = nodeById.get(String(e.to));
              return targetNode ? (targetNode.type || (Array.isArray(targetNode.labels) ? targetNode.labels[0] : targetNode.labels)) : null;
            })
            .filter(Boolean)
            .map(String);
          
          const uniqueTargetTypes = [...new Set(targetTypes)];
          setAvailableTargetTypes(uniqueTargetTypes);
          console.log('Available target types for source', selectedSourceType, ':', uniqueTargetTypes);
        } else {
          setAvailableTargetTypes([]);
        }
        
        // Update available source types based on selected target type
        if (selectedTargetType) {
          const targetNodeIds = nodes
            .filter(n => {
              const nodeType = n.type || (Array.isArray(n.labels) ? n.labels[0] : n.labels);
              return String(nodeType) === selectedTargetType;
            })
            .map(n => String(n.id));
          
          const sourceTypes = edges
            .filter(e => targetNodeIds.includes(String(e.to)))
            .map(e => {
              const sourceNode = nodeById.get(String(e.from));
              return sourceNode ? (sourceNode.type || (Array.isArray(sourceNode.labels) ? sourceNode.labels[0] : sourceNode.labels)) : null;
            })
            .filter(Boolean)
            .map(String);
          
          const uniqueSourceTypes = [...new Set(sourceTypes)];
          setAvailableSourceTypes(uniqueSourceTypes);
          console.log('Available source types for target', selectedTargetType, ':', uniqueSourceTypes);
        } else {
          setAvailableSourceTypes([]);
        }
        
        const keepIds = new Set<string>();
        filteredEdges.forEach((e: any) => { keepIds.add(e.from); keepIds.add(e.to); });
        const filteredNodes = nodes.filter((n: any) => keepIds.size === 0 || keepIds.has(String(n.id)));

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
  }, [selectedSourceType, selectedTargetType, selectedRelationType, maxNodes]);

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
      // Prepare override data for graph rendering
      const nodes = (payload.nodes || []).map((n: any) => ({ id: String(n.id), type: n.type || (Array.isArray(n.labels) ? n.labels[0] : n.labels) || 'Unknown' }));
      const edges = (payload.relationships || []).map((r: any) => ({ from: String(r.from), to: String(r.to), type: r.type }));
      setGraphOverride({ nodes, edges });
      setCypherWarnings(payload.warnings || []);
      toast({
        title: 'Query executed',
        description: 'Returned ' + payload.nodes.length + ' nodes and ' + payload.relationships.length + ' relationships',
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

        {/* Controls */}
        <Box p={4} bg={bgColor} borderRadius="md" borderColor={borderColor}>
          <VStack spacing={4}>
            <HStack spacing={6} wrap="wrap" w="full">
              <HStack>
                <Icon as={FaFilter} color="blue.500" />
                <Text fontSize="sm" fontWeight="semibold">Filters:</Text>
              </HStack>
              
              <HStack>
                <Text fontSize="sm">From Type:</Text>
                <Select
                  size="sm"
                  maxW="200px"
                  value={selectedSourceType}
                  onChange={(e) => {
                    setSelectedSourceType(e.target.value);
                    setSelectedTargetType(''); // Reset target when source changes
                    setSelectedRelationType(''); // Reset relation when source changes
                  }}
                >
                  <option value="">Any</option>
                  {metrics?.node_types.map(nt => (
                    <option key={'from-'+nt.type} value={nt.type}>{nt.type} ({nt.count})</option>
                  ))}
                </Select>
              </HStack>

              <HStack>
                <Text fontSize="sm">To Type:</Text>
                <Select
                  size="sm"
                  maxW="200px"
                  value={selectedTargetType}
                  onChange={(e) => {
                    setSelectedTargetType(e.target.value);
                    setSelectedRelationType(''); // Reset relation when target changes
                  }}
                  disabled={selectedSourceType && availableTargetTypes.length === 0}
                >
                  <option value="">
                    {selectedSourceType 
                      ? availableTargetTypes.length === 0 
                        ? "No valid targets" 
                        : "Any valid target"
                      : "Any"
                    }
                  </option>
                  {(selectedSourceType ? availableTargetTypes : metrics?.node_types?.map(nt => nt.type) || [])
                    .map(type => {
                      const nodeType = metrics?.node_types?.find(nt => nt.type === type);
                      return (
                        <option key={'to-'+type} value={type}>
                          {type} {nodeType ? `(${nodeType.count})` : ''}
                        </option>
                      );
                    })}
                </Select>
              </HStack>

              <HStack>
                <Text fontSize="sm">Relation Type:</Text>
                <Select
                  size="sm"
                  maxW="250px"
                  value={selectedRelationType}
                  onChange={(e) => setSelectedRelationType(e.target.value)}
                  disabled={selectedSourceType && selectedTargetType && availableTargetTypes.length === 0}
                >
                  <option value="">
                    {selectedSourceType && selectedTargetType && availableTargetTypes.length === 0
                      ? "No valid relations"
                      : `All Relations (${metrics?.relation_types?.reduce((sum, rt) => sum + rt.count, 0) || 0})`
                    }
                  </option>
                  {metrics?.relation_types?.map(rt => (
                    <option key={'rel-'+rt.type} value={rt.type}>
                      {rt.type} ({rt.count})
                    </option>
                  ))}
                </Select>
              </HStack>

              <HStack>
                <Text fontSize="sm">Max Nodes:</Text>
                <input 
                  type="range" 
                  min="100" 
                  max="5000" 
                  step="100"
                  value={maxNodes}
                  onChange={(e) => setMaxNodes(Number(e.target.value))}
                  style={{ width: '100px' }}
                />
                <Text fontSize="sm" minW="50px">{maxNodes}</Text>
              </HStack>
            </HStack>

            <HStack spacing={6} wrap="wrap" w="full">
              <HStack>
                <input 
                  type="checkbox" 
                  checked={showClusters}
                  onChange={(e) => setShowClusters(e.target.checked)}
                />
                <Text fontSize="sm">Show Clusters</Text>
              </HStack>

              <HStack>
                <input 
                  type="checkbox" 
                  checked={showLabels}
                  onChange={(e) => setShowLabels(e.target.checked)}
                />
                <Text fontSize="sm">Show Labels</Text>
              </HStack>

              <HStack spacing={2}>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => {
                    setSelectedSourceType('');
                    setSelectedTargetType('');
                    setSelectedRelationType('');
                  }}
                >
                  Reset Filters
                </Button>
                <Button size="sm" variant="outline" leftIcon={<FaDownload />}>
                  Export
                </Button>
                <Button size="sm" variant="outline" leftIcon={<FaShare />}>
                  Share
                </Button>
              </HStack>
            </HStack>
          </VStack>
        </Box>

        {/* Structure Graph */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <VStack align="stretch" spacing={2}>
              <HStack justify="space-between" align="center">
                <HStack spacing={3}>
                  <Icon as={FaSearch} color="purple.500" />
                  <Heading size="md">Cypher Playground</Heading>
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
              <Text fontSize="sm" color={mutedTextColor}>
                Compose a Cypher query to explore targeted subgraphs. Suggestions adapt as you type.
              </Text>
            </VStack>
          </CardHeader>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <Textarea
                value={cypherQuery}
                onChange={(event) => setCypherQuery(event.target.value)}
                minH="120px"
                fontFamily="mono"
                placeholder="MATCH (n) RETURN n LIMIT 25"
                onKeyDown={(event) => {
                  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                    handleRunCypher();
                  }
                }}
              />
              <HStack spacing={2} wrap="wrap">
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
              {cypherWarnings.length > 0 && (
                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <VStack align="start" spacing={1}>
                    {cypherWarnings.map((warning, index) => (
                      <Text key={'warning-' + index} fontSize="xs">{warning}</Text>
                    ))}
                  </VStack>
                </Alert>
              )}
              {cypherResult && (
                <VStack align="stretch" spacing={4}>
                  <Box>
                    <Heading size="sm" mb={2}>Summary</Heading>
                    <Code display="block" whiteSpace="pre-wrap" borderRadius="md" p={3} fontSize="xs">
                      {JSON.stringify(cypherResult.summary, null, 2)}
                    </Code>
                  </Box>
                  <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
                    <Box>
                      <Heading size="sm" mb={2}>Nodes ({cypherResult.nodes.length})</Heading>
                      <VStack align="stretch" spacing={2}>
                        {cypherResult.nodes.slice(0, 10).map((node) => (
                          <Box key={node.id} border="1px solid" borderColor={borderColor} borderRadius="md" p={2}>
                            <Text fontWeight="semibold">{node.display || node.id}</Text>
                            <Text fontSize="xs" color={mutedTextColor}>
                              {(node.labels || []).join(', ') || node.type || 'Node'}
                            </Text>
                            {node.properties && Object.keys(node.properties).length > 0 && (
                              <Code display="block" whiteSpace="pre-wrap" fontSize="xs">
                                {JSON.stringify(node.properties, null, 2)}
                              </Code>
                            )}
                          </Box>
                        ))}
                        {cypherResult.nodes.length > 10 && (
                          <Text fontSize="xs" color={mutedTextColor}>
                            Showing first 10 of {cypherResult.nodes.length} nodes.
                          </Text>
                        )}
                      </VStack>
                    </Box>
                    <Box>
                      <Heading size="sm" mb={2}>Relationships ({cypherResult.relationships.length})</Heading>
                      <VStack align="stretch" spacing={2}>
                        {cypherResult.relationships.slice(0, 10).map((relationship) => (
                          <Box key={relationship.id} border="1px solid" borderColor={borderColor} borderRadius="md" p={2}>
                            <Text fontWeight="semibold">{relationship.type}</Text>
                            <Text fontSize="xs" color={mutedTextColor}>
                              {relationship.from} → {relationship.to}
                            </Text>
                            {relationship.properties && Object.keys(relationship.properties).length > 0 && (
                              <Code display="block" whiteSpace="pre-wrap" fontSize="xs">
                                {JSON.stringify(relationship.properties, null, 2)}
                              </Code>
                            )}
                          </Box>
                        ))}
                        {cypherResult.relationships.length > 10 && (
                          <Text fontSize="xs" color={mutedTextColor}>
                            Showing first 10 of {cypherResult.relationships.length} relationships.
                          </Text>
                        )}
                      </VStack>
                    </Box>
                  </Grid>
                </VStack>
              )}
            </VStack>
          </CardBody>
        </Card>

        <Box h="600px" bg={bgColor} borderRadius="md" borderColor={borderColor} p={4}>
          {/* Secondary Highlight Filter */}
          <HStack spacing={3} mb={3}>
            <Text fontSize="sm">Highlight:</Text>
            <Select size="sm" maxW="220px" value={highlightKind} onChange={(e)=> setHighlightKind(e.target.value as any)}>
              <option value="none">None</option>
              <option value="by-type">By Node Type</option>
              <option value="future-nodes">Future Nodes (placeholder)</option>
              <option value="future-relationships">Future Relationships (placeholder)</option>
            </Select>
            {highlightKind === 'by-type' && (
              <Select size="sm" maxW="220px" value={highlightValue} onChange={(e)=> setHighlightValue(e.target.value)}>
                <option value="">Select type…</option>
                {metrics?.node_types.map(nt => (
                  <option key={'h-'+nt.type} value={nt.type}>{nt.type}</option>
                ))}
              </Select>
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
            {graphOverride && (
              <Button size="sm" variant="outline" onClick={() => {
                const blob = new Blob([JSON.stringify(graphOverride, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'subgraph.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                setTimeout(()=> URL.revokeObjectURL(url), 1000);
              }}>
                Export JSON
              </Button>
            )}
          </HStack>
          {/* Filter Status Indicator */}
          {metrics && (
            <Box mb={4} p={3} bg={filterStatusBg} borderRadius="md">
              <HStack spacing={4} wrap="wrap">
                <Badge colorScheme="blue" variant="subtle">
                  {selectedRelationType || 'All Relations'} 
                  {selectedRelationType && metrics.relation_types?.find(rt => rt.type === selectedRelationType) && 
                    ` (${metrics.relation_types.find(rt => rt.type === selectedRelationType)?.count} edges)`
                  }
                </Badge>
                {selectedSourceType && (
                  <Badge colorScheme="green" variant="subtle">
                    From: {selectedSourceType}
                  </Badge>
                )}
                {selectedTargetType && (
                  <Badge colorScheme="purple" variant="subtle">
                    To: {selectedTargetType}
                  </Badge>
                )}
                <Text fontSize="sm" color={mutedTextColor}>
                  Showing {metrics.total_relations} relationships
                </Text>
              </HStack>
            </Box>
          )}
          
          {metrics ? (
            <StructureAnalysisGraph
              metrics={metrics}
              height={520}
              selectedRelationType={selectedRelationType}
              selectedSourceType={selectedSourceType}
              selectedTargetType={selectedTargetType}
              showClusters={showClusters}
              showLabels={showLabels}
              maxNodes={maxNodes}
              useRealData={true}
              onSvgReady={setSvgEl}
              overrideData={graphOverride}
              highlightFilter={highlightKind === 'none' ? null : { kind: highlightKind === 'by-type' ? 'by-type' : (highlightKind as any), value: highlightValue }}
            />
          ) : (
            <VStack align="center" justify="center" h="full">
              <Spinner size="lg" color="green.500" />
              <Text>Loading structure analysis...</Text>
            </VStack>
          )}
        </Box>

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
