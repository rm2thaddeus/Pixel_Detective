'use client';
import { Box, Heading, Spinner, Text, VStack, HStack, Button, Select, Badge, Grid, GridItem, Card, CardBody, CardHeader, Divider, useColorModeValue } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';

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

interface Node {
  id: string;
  labels: string[];
  type: string;
  [key: string]: any;
}

interface Relation {
  from: string;
  to: string;
  type: string;
}

export default function EnhancedDevGraphPage() {
  const [stats, setStats] = useState<any>(null);
  const [nodeTypes, setNodeTypes] = useState<NodeType[]>([]);
  const [relationTypes, setRelationTypes] = useState<RelationType[]>([]);
  const [selectedNodeType, setSelectedNodeType] = useState<string>('');
  const [selectedRelationType, setSelectedRelationType] = useState<string>('');
  const [nodes, setNodes] = useState<Node[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingNodes, setLoadingNodes] = useState(false);
  const [loadingRelations, setLoadingRelations] = useState(false);

  // All hooks must be called before any conditional returns
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const pageBgColor = useColorModeValue('gray.50', 'gray.900');

  // Color scheme for different node types
  const nodeTypeColors: Record<string, string> = {
    'Requirement': 'blue',
    'Sprint': 'green',
    'Document': 'purple',
    'Chunk': 'orange',
    'Commit': 'red',
    'File': 'teal',
    'Goal': 'pink',
    'Unknown': 'gray'
  };

  // Color scheme for different relation types
  const relationTypeColors: Record<string, string> = {
    'TOUCHES': 'red',
    'TOUCHED': 'red',
    'MODIFIED': 'cyan',
    'CONTAINS_DOC': 'blue',
    'CONTAINS_CHUNK': 'green',
    'MENTIONS': 'purple',
    'PART_OF': 'orange',
    'IMPLEMENTS': 'teal',
    'DEPENDS_ON': 'yellow',
    'EVOLVES_FROM': 'pink',
    'REFERENCES': 'cyan',
    'RELATES_TO': 'gray'
  };

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [nodesRes, relationsRes, commitsRes] = await Promise.all([
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes/count`),
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations/count`),
          fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=5`)
        ]);

        const [nodes, relations, commits] = await Promise.all([
          nodesRes.json(),
          relationsRes.json(),
          commitsRes.json()
        ]);

        setStats({ nodes, relations, commits });
        
        // Analyze node types from sample data
        await analyzeNodeTypes();
        await analyzeRelationTypes();
        
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  const analyzeNodeTypes = async () => {
    try {
      const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes?limit=1000`);
      const nodes: Node[] = await response.json();
      
      const typeCounts: Record<string, number> = {};
      nodes.forEach(node => {
        const type = node.type || 'Unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
      });
      
      const nodeTypes: NodeType[] = Object.entries(typeCounts).map(([type, count]) => ({
        type,
        count,
        color: nodeTypeColors[type] || 'gray'
      }));
      
      setNodeTypes(nodeTypes);
    } catch (error) {
      console.error('Failed to analyze node types:', error);
    }
  };

  const analyzeRelationTypes = async () => {
    try {
      const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations?limit=1000`);
      const relations: Relation[] = await response.json();
      
      const typeCounts: Record<string, number> = {};
      relations.forEach(relation => {
        const type = relation.type || 'RELATES_TO';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
      });
      
      const relationTypes: RelationType[] = Object.entries(typeCounts).map(([type, count]) => ({
        type,
        count,
        color: relationTypeColors[type] || 'gray'
      }));
      
      setRelationTypes(relationTypes);
    } catch (error) {
      console.error('Failed to analyze relation types:', error);
    }
  };

  const fetchNodesByType = async (nodeType: string) => {
    setLoadingNodes(true);
    try {
      const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/nodes?node_type=${nodeType}&limit=100`);
      const nodes: Node[] = await response.json();
      setNodes(nodes);
    } catch (error) {
      console.error('Failed to fetch nodes:', error);
    } finally {
      setLoadingNodes(false);
    }
  };

  const fetchRelationsByType = async (relationType: string) => {
    setLoadingRelations(true);
    try {
      const response = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/relations?rel_type=${relationType}&limit=100`);
      const relations: Relation[] = await response.json();
      setRelations(relations);
    } catch (error) {
      console.error('Failed to fetch relations:', error);
    } finally {
      setLoadingRelations(false);
    }
  };

  const handleNodeTypeChange = (nodeType: string) => {
    setSelectedNodeType(nodeType);
    if (nodeType) {
      fetchNodesByType(nodeType);
    } else {
      setNodes([]);
    }
  };

  const handleRelationTypeChange = (relationType: string) => {
    setSelectedRelationType(relationType);
    if (relationType) {
      fetchRelationsByType(relationType);
    } else {
      setRelations([]);
    }
  };

  if (loading) {
    return (
      <Box minH="100vh">
        <Header />
        <VStack spacing={4} p={8}>
          <Spinner size="xl" color="blue.500" />
          <Text>Loading Enhanced Dev Graph...</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg={pageBgColor}>
      <Header />
      <VStack spacing={6} p={8} align="stretch" maxW="7xl" mx="auto">
        <Heading size="lg" color="blue.600">
          Enhanced Developer Graph Dashboard
        </Heading>
        
        {/* Simple Navigation */}
        <Box p={4} bg="gray.50" borderRadius="md">
          <Text fontSize="sm" fontWeight="medium" mb={2}>Navigate to other views:</Text>
          <HStack spacing={4}>
            <Text fontSize="sm" color="blue.600"><a href="/dev-graph/complex">Complex View</a></Text>
            <Text fontSize="sm">•</Text>
            <Text fontSize="sm" color="green.600" fontWeight="bold">Enhanced Dashboard (Current)</Text>
            <Text fontSize="sm">•</Text>
            <Text fontSize="sm" color="purple.600"><a href="/dev-graph/simple">Simple Dashboard</a></Text>
          </HStack>
        </Box>
        
        {stats && (
          <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={6}>
            {/* Graph Statistics */}
            <GridItem>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <Heading size="md">Graph Statistics</Heading>
                </CardHeader>
                <CardBody>
                  <VStack align="stretch" spacing={3}>
                    <HStack justify="space-between">
                      <Text><strong>Total Nodes:</strong></Text>
                      <Badge colorScheme="blue" fontSize="md">{stats.nodes.total}</Badge>
                    </HStack>
                    <HStack justify="space-between">
                      <Text><strong>Total Relations:</strong></Text>
                      <Badge colorScheme="green" fontSize="md">{stats.relations.total}</Badge>
                    </HStack>
                    <HStack justify="space-between">
                      <Text><strong>Recent Commits:</strong></Text>
                      <Badge colorScheme="purple" fontSize="md">{stats.commits.length}</Badge>
                    </HStack>
                  </VStack>
                </CardBody>
              </Card>
            </GridItem>

            {/* Node Types */}
            <GridItem>
              <Card bg={bgColor} borderColor={borderColor}>
                <CardHeader>
                  <Heading size="md">Node Types</Heading>
                </CardHeader>
                <CardBody>
                  <VStack align="stretch" spacing={2}>
                    {nodeTypes.map((nodeType) => (
                      <HStack key={nodeType.type} justify="space-between">
                        <HStack>
                          <Box w={3} h={3} bg={`${nodeType.color}.500`} borderRadius="full" />
                          <Text fontSize="sm">{nodeType.type}</Text>
                        </HStack>
                        <Badge colorScheme={nodeType.color} variant="subtle">
                          {nodeType.count}
                        </Badge>
                      </HStack>
                    ))}
                  </VStack>
                </CardBody>
              </Card>
            </GridItem>
          </Grid>
        )}

        {/* Relation Types */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <Heading size="md">Relation Types</Heading>
          </CardHeader>
          <CardBody>
            <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" }} gap={3}>
              {relationTypes.map((relationType) => (
                <HStack key={relationType.type} justify="space-between" p={2} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                  <HStack>
                    <Box w={3} h={3} bg={`${relationType.color}.500`} borderRadius="full" />
                    <Text fontSize="sm">{relationType.type}</Text>
                  </HStack>
                  <Badge colorScheme={relationType.color} variant="subtle">
                    {relationType.count}
                  </Badge>
                </HStack>
              ))}
            </Grid>
          </CardBody>
        </Card>

        {/* Node Explorer */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <Heading size="md">Node Explorer</Heading>
          </CardHeader>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <HStack>
                <Select
                  placeholder="Select node type to explore"
                  value={selectedNodeType}
                  onChange={(e) => handleNodeTypeChange(e.target.value)}
                >
                  {nodeTypes.map((nodeType) => (
                    <option key={nodeType.type} value={nodeType.type}>
                      {nodeType.type} ({nodeType.count})
                    </option>
                  ))}
                </Select>
                <Button
                  colorScheme="blue"
                  onClick={() => window.open(`${DEV_GRAPH_API_URL}/docs`, '_blank')}
                >
                  API Docs
                </Button>
              </HStack>
              
              {loadingNodes && <Spinner />}
              
              {nodes.length > 0 && (
                <Box>
                  <Text fontSize="sm" color="gray.600" mb={2}>
                    Showing {nodes.length} nodes of type "{selectedNodeType}"
                  </Text>
                  <VStack align="stretch" spacing={2} maxH="400px" overflowY="auto">
                    {nodes.slice(0, 20).map((node) => (
                      <Box key={node.id} p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                        <Text fontSize="sm" fontWeight="bold">{node.id}</Text>
                        {node.description && (
                          <Text fontSize="xs" color="gray.600" noOfLines={2}>
                            {node.description}
                          </Text>
                        )}
                        {node.path && (
                          <Text fontSize="xs" color="blue.600">
                            {node.path}
                          </Text>
                        )}
                        {node.message && (
                          <Text fontSize="xs" color="gray.600" noOfLines={1}>
                            {node.message}
                          </Text>
                        )}
                      </Box>
                    ))}
                    {nodes.length > 20 && (
                      <Text fontSize="xs" color="gray.500" textAlign="center">
                        ... and {nodes.length - 20} more
                      </Text>
                    )}
                  </VStack>
                </Box>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Relation Explorer */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <Heading size="md">Relation Explorer</Heading>
          </CardHeader>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <HStack>
                <Select
                  placeholder="Select relation type to explore"
                  value={selectedRelationType}
                  onChange={(e) => handleRelationTypeChange(e.target.value)}
                >
                  {relationTypes.map((relationType) => (
                    <option key={relationType.type} value={relationType.type}>
                      {relationType.type} ({relationType.count})
                    </option>
                  ))}
                </Select>
              </HStack>
              
              {loadingRelations && <Spinner />}
              
              {relations.length > 0 && (
                <Box>
                  <Text fontSize="sm" color="gray.600" mb={2}>
                    Showing {relations.length} relations of type "{selectedRelationType}"
                  </Text>
                  <VStack align="stretch" spacing={2} maxH="400px" overflowY="auto">
                    {relations.slice(0, 20).map((relation, index) => (
                      <HStack key={index} p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                        <Text fontSize="sm" fontWeight="bold" color="blue.600">
                          {relation.from}
                        </Text>
                        <Badge colorScheme={relationTypeColors[relation.type] || 'gray'} variant="subtle">
                          {relation.type}
                        </Badge>
                        <Text fontSize="sm" fontWeight="bold" color="green.600">
                          {relation.to}
                        </Text>
                      </HStack>
                    ))}
                    {relations.length > 20 && (
                      <Text fontSize="xs" color="gray.500" textAlign="center">
                        ... and {relations.length - 20} more
                      </Text>
                    )}
                  </VStack>
                </Box>
              )}
            </VStack>
          </CardBody>
        </Card>

        {/* Recent Commits */}
        {stats?.commits && stats.commits.length > 0 && (
          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <Heading size="md">Recent Commits</Heading>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={2}>
                {stats.commits.slice(0, 5).map((commit: any, index: number) => (
                  <Box key={commit.hash} p={3} bg={useColorModeValue('gray.50', 'gray.700')} borderRadius="md">
                    <Text fontSize="sm" fontWeight="bold">{commit.message}</Text>
                    <Text fontSize="xs" color="gray.600">
                      {commit.author_name} • {new Date(commit.timestamp).toLocaleDateString()}
                    </Text>
                    {commit.files_changed && (
                      <Text fontSize="xs" color="blue.600">
                        {commit.files_changed.length} files changed
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Box>
  );
}
