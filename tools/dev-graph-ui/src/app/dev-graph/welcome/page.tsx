'use client';
import { Box, Heading, Text, VStack, HStack, Grid, GridItem, Card, CardBody, CardHeader, Badge, Button, Spinner, Alert, AlertIcon, useColorModeValue, Stat, StatLabel, StatNumber, StatHelpText, StatArrow, Progress, Divider, Icon, Flex, Select } from '@chakra-ui/react';
import { useState, useEffect, useMemo } from 'react';
import { Header } from '@/components/Header';
import { Link as ChakraLink } from '@chakra-ui/react';
import { FaCode, FaGitAlt, FaFileAlt, FaProjectDiagram, FaClock, FaUsers, FaChartLine, FaExclamationTriangle, FaCheckCircle, FaTimesCircle } from 'react-icons/fa';
import { useAnalytics, useTelemetry, useWindowedSubgraph, useDataQuality } from '../hooks/useWindowedSubgraph';
import { useQuery } from '@tanstack/react-query';

// Developer Graph API base URL
const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

interface SystemHealth {
  api_connected: boolean;
  database_connected: boolean;
  last_ingestion: string | null;
  data_quality_score: number;
  total_nodes: number;
  total_relations: number;
  recent_commits: number;
  active_sprints: number;
  node_types: Array<{ type: string; count: number; color: string }>;
  relation_types: Array<{ type: string; count: number; color: string }>;
  performance_metrics: {
    avg_query_time_ms: number;
    cache_hit_rate: number;
    memory_usage_mb: number;
  };
}

interface QualityIndicator {
  label: string;
  value: number | string | null | undefined;
  target?: number | null | undefined;
  unit?: string;
  status?: string;
  description?: string;
}

interface QualitySection {
  key: string;
  label: string;
  score: number;
  max_score: number;
  summary: string;
  indicators: QualityIndicator[];
}

interface QualityCategory {
  key: string;
  label: string;
  score: number;
  max_score: number;
  summary: string;
  sections: QualitySection[];
}

export default function WelcomeDashboard() {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const pageBgColor = useColorModeValue('gray.50', 'gray.900');
  const indicatorBgColor = useColorModeValue('gray.100', 'gray.700');

  // Use new hooks for data fetching
  const { data: analyticsData, isLoading: analyticsLoading, error: analyticsError } = useAnalytics();
  const { data: telemetryData, isLoading: telemetryLoading, error: telemetryError } = useTelemetry();
  const { data: subgraphData, isLoading: subgraphLoading, error: subgraphError } = useWindowedSubgraph({ limit: 10 });
  const { data: dataQuality, isLoading: dataQualityLoading, error: dataQualityError } = useDataQuality();
  
  // Fetch additional data using React Query
  const { data: commitsData, isLoading: commitsLoading } = useQuery({
    queryKey: ['commits', 'recent'],
    queryFn: async () => {
      const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=5`);
      if (!res.ok) throw new Error('Failed to fetch commits');
      return res.json();
    },
    staleTime: 60_000,
  });

  // Fetch all commits for data quality calculation
  const { data: allCommitsData, isLoading: allCommitsLoading } = useQuery({
    queryKey: ['commits', 'all'],
    queryFn: async () => {
      const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/commits?limit=1000`);
      if (!res.ok) throw new Error('Failed to fetch all commits');
      return res.json();
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  const { data: sprintsData, isLoading: sprintsLoading } = useQuery({
    queryKey: ['sprints'],
    queryFn: async () => {
      const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/sprints`);
      if (!res.ok) throw new Error('Failed to fetch sprints');
      return res.json();
    },
    staleTime: 60_000,
  });

  // Calculate loading and error states
  const loading = analyticsLoading || telemetryLoading || subgraphLoading || commitsLoading || allCommitsLoading || sprintsLoading || dataQualityLoading;
  const error = analyticsError || telemetryError || subgraphError || dataQualityError;

  // Helper functions for node and relation type colors
  const getNodeTypeColor = (type: string) => {
    const colors = {
      'commits': '#3182ce',
      'files': '#38a169',
      'requirements': '#d69e2e',
      'sprints': '#805ad5',
      'documents': '#e53e3e',
      'chunks': '#dd6b20'
    };
    return colors[type as keyof typeof colors] || '#718096';
  };

  const getRelationTypeColor = (type: string) => {
    const colors = {
      'TOUCHED': '#3182ce',
      'IMPLEMENTS': '#38a169',
      'EVOLVES_FROM': '#d69e2e',
      'REFACTORED_TO': '#805ad5',
      'DEPRECATED_BY': '#e53e3e',
      'MENTIONS': '#dd6b20',
      'CONTAINS_CHUNK': '#2d3748',
      'CONTAINS_DOC': '#4a5568',
      'REFERENCES': '#2b6cb0',
      'PART_OF': '#744210'
    };
    return colors[type as keyof typeof colors] || '#718096';
  };

  // Process data into SystemHealth format
  const qualityCategories = useMemo<QualityCategory[]>(() => {
    if (!dataQuality) {
      return [
        {
          key: 'data_quality',
          label: 'Data Quality',
          score: 0,
          max_score: 100,
          summary: 'Data quality metrics not available yet – trigger an ingest to populate metrics.',
          sections: [
            {
              key: 'no-data',
              label: 'No metrics available',
              score: 0,
              max_score: 100,
              summary: 'Once the developer graph ingest completes this panel will populate automatically.',
              indicators: [],
            },
          ],
        },
      ];
    }

    const schemaEntries = Object.entries(dataQuality.schema || {});
    const schemaScore = schemaEntries.filter(([, present]) => present).length;
    const schemaMax = Math.max(schemaEntries.length, 1);

    const relationshipEntries = Object.entries(dataQuality.relationships || {});
    const temporalEntries = Object.entries(dataQuality.temporal || {});

    return [
      {
        key: 'data_quality',
        label: 'Data Quality',
        score: dataQuality.data_quality_score ?? 0,
        max_score: 100,
        summary: 'Graph integrity metrics from automated ingest assertions.',
        sections: [
          {
            key: 'graph-integrity',
            label: 'Graph Integrity',
            score: dataQuality.data_quality_score ?? 0,
            max_score: 100,
            summary: 'Core counts used to grade the graph snapshot.',
            indicators: [
              {
                label: 'TOUCHED relationships',
                value: dataQuality.touched_relationships ?? 0,
                status: (dataQuality.touched_relationships ?? 0) > 0 ? 'ok' : 'warn',
              },
              {
                label: 'Orphaned nodes',
                value: dataQuality.orphaned_nodes ?? 0,
                status: (dataQuality.orphaned_nodes ?? 0) > 0 ? 'warn' : 'ok',
              },
              {
                label: 'Timestamp issues',
                value: dataQuality.timestamp_issues ?? 0,
                status: (dataQuality.timestamp_issues ?? 0) > 0 ? 'warn' : 'ok',
              },
            ],
          },
          {
            key: 'temporal-consistency',
            label: 'Temporal Consistency',
            score: Math.max(
              0,
              100 - temporalEntries.reduce((sum, [, value]) => sum + (value ?? 0), 0),
            ),
            max_score: 100,
            summary: 'Missing timestamps detected on temporal relationships.',
            indicators: temporalEntries.map(([label, value]) => ({
              label,
              value,
              status: (value ?? 0) > 0 ? 'warn' : 'ok',
            })),
          },
        ],
      },
      {
        key: 'schema',
        label: 'Schema Coverage',
        score: schemaScore,
        max_score: schemaMax,
        summary: 'Neo4j schema and relationship coverage checks.',
        sections: [
          {
            key: 'schema-status',
            label: 'Schema Status',
            score: schemaScore,
            max_score: schemaMax,
            summary: 'Presence of core nodes, documents and constraints.',
            indicators: schemaEntries.map(([label, present]) => ({
              label,
              value: present ? 'Present' : 'Missing',
              status: present ? 'ok' : 'warn',
            })),
          },
          {
            key: 'relationship-coverage',
            label: 'Relationship Coverage',
            score: relationshipEntries.length,
            max_score: Math.max(relationshipEntries.length, 1),
            summary: 'Counts surfaced by the validator across relationship types.',
            indicators: relationshipEntries.map(([label, value]) => ({
              label,
              value,
              status: (value ?? 0) > 0 ? 'ok' : 'warn',
            })),
          },
        ],
      },
    ];
  }, [dataQuality]);
  const [selectedQualityCategory, setSelectedQualityCategory] = useState<string>('data_quality');

  useEffect(() => {
    if (qualityCategories.length === 0) return;
    if (!qualityCategories.some(category => category.key === selectedQualityCategory)) {
      setSelectedQualityCategory(qualityCategories[0].key);
    }
  }, [qualityCategories, selectedQualityCategory]);

  const selectedCategory = qualityCategories.find(category => category.key === selectedQualityCategory) || qualityCategories[0];
  const dataQualityCategory = qualityCategories.find(category => category.key === 'data_quality') || selectedCategory;

  const baselineScore = Math.round(dataQualityCategory?.score ?? 0);
  const activeScore = Math.round(selectedCategory?.score ?? baselineScore);
  const selectedPercent = selectedCategory ? Math.min(100, (selectedCategory.score / selectedCategory.max_score) * 100) : 0;
  const selectedSections = selectedCategory?.sections ?? [];

  const indicatorStatusColor: Record<string, string> = {
    ok: 'green',
    good: 'green',
    excellent: 'green',
    warn: 'yellow',
    warning: 'yellow',
    poor: 'red',
    critical: 'red',
    unknown: 'gray'
  };

  const formatIndicatorValue = (value: number | string | null | undefined, unit?: string) => {
    // Handle null, undefined, or invalid values
    if (value === null || value === undefined) {
      return unit ? 'N/A' + unit : 'N/A';
    }
    
    if (typeof value === 'number') {
      const safeNumber = Number.isFinite(value) ? value : 0;
      const formatted = Number.isInteger(safeNumber) ? safeNumber.toString() : safeNumber.toFixed(2).replace(/\.00$/, '');
      return unit ? formatted + unit : formatted;
    }
    
    const textValue = value.toString();
    return unit ? textValue + unit : textValue;
  };

  const statsSummary = telemetryData?.summary ?? {
    total_nodes: analyticsData?.graph?.total_nodes ?? 0,
    total_relationships: analyticsData?.graph?.total_edges ?? 0,
    recent_commits_7d: analyticsData?.activity?.peak_activity?.count ?? 0,
  };

  const fallbackNodeTypes = Object.entries(analyticsData?.graph?.node_types || {}).map(([type, count]) => ({
    type,
    count: count as number,
    color: getNodeTypeColor(type),
  }));

  const fallbackRelTypes = Object.entries(analyticsData?.graph?.edge_types || {})
    .map(([type, count]) => ({
      type,
      count: count as number,
      color: getRelationTypeColor(type),
    }))
    .sort((a, b) => b.count - a.count);

  const nodeTypes = (telemetryData?.node_types?.length ? telemetryData.node_types : fallbackNodeTypes) ?? [];
  const relationTypes = (telemetryData?.relationship_types?.length ? telemetryData.relationship_types : fallbackRelTypes) ?? [];

  const health: SystemHealth = {
    api_connected: !analyticsError,
    database_connected: !telemetryError,
    last_ingestion: analyticsData?.activity?.peak_activity?.timestamp ?? null,
    data_quality_score: baselineScore,
    total_nodes: statsSummary.total_nodes ?? 0,
    total_relations: statsSummary.total_relationships ?? 0,
    recent_commits: statsSummary.recent_commits_7d ?? 0,
    active_sprints: Array.isArray(sprintsData) ? sprintsData.length : 0,
    node_types: nodeTypes,
    relation_types: relationTypes,
    performance_metrics: {
      avg_query_time_ms: telemetryData?.avg_query_time_ms ?? 0,
      cache_hit_rate: telemetryData?.cache_hit_rate ?? 0,
      memory_usage_mb: telemetryData?.memory_usage_mb ?? 0,
    },
  };

  const nodeTypeSummary = (health.node_types ?? []).slice(0, 6);
  const relationTypeSummary = (health.relation_types ?? []).slice(0, 6);

  const getHealthStatus = (score: number) => {
    if (score >= 80) return { status: 'excellent', color: 'green', icon: FaCheckCircle };
    if (score >= 60) return { status: 'good', color: 'blue', icon: FaCheckCircle };
    if (score >= 40) return { status: 'fair', color: 'yellow', icon: FaExclamationTriangle };
    return { status: 'poor', color: 'red', icon: FaTimesCircle };
  };

  if (loading) {
    return (
      <Box minH="100vh" bg={pageBgColor}>
        <Header />
        <VStack spacing={4} p={8} align="center" justify="center" minH="60vh">
          <Spinner size="xl" color="blue.500" />
          <Text>Loading Developer Graph Dashboard...</Text>
        </VStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box minH="100vh" bg={pageBgColor}>
        <Header />
        <VStack spacing={4} p={8} align="center" justify="center" minH="60vh">
          <Alert status="error" maxW="md">
            <AlertIcon />
            <VStack align="start" spacing={2}>
              <Text fontWeight="bold">Failed to load dashboard data</Text>
              <Text fontSize="sm">{error instanceof Error ? error.message : 'Unknown error'}</Text>
            </VStack>
          </Alert>
        </VStack>
      </Box>
    );
  }

  const baselineHealth = getHealthStatus(baselineScore);
  const selectedHealth = getHealthStatus(activeScore);

  return (
    <Box minH="100vh" bg={pageBgColor}>
      <Header />
      <VStack spacing={8} p={8} align="stretch" maxW="7xl" mx="auto">
        {/* Welcome Header */}
        <Box textAlign="center" py={8}>
          <Heading size="2xl" color="blue.600" mb={4}>
            Developer Graph Explorer
          </Heading>
          <Text fontSize="xl" color="gray.600" maxW="2xl" mx="auto">
            Explore your codebase evolution through biological metaphors. 
            Watch files evolve like organisms, commits as generations, and branches as lineages.
          </Text>
        </Box>

        {/* System Health Overview */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <HStack>
              <Icon as={baselineHealth.icon} color={`${baselineHealth.color}.500`} />
              <Heading size="md">System Health</Heading>
              <Badge colorScheme={baselineHealth.color} ml="auto">
                {baselineHealth.status.toUpperCase()}
              </Badge>
            </HStack>
          </CardHeader>
          <CardBody>
            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={6}>
              <Stat>
                <StatLabel>{selectedCategory ? selectedCategory.label + ' Score' : 'Data Quality Score'}</StatLabel>
                {qualityCategories.length > 1 && (
                  <Select
                    size="xs"
                    value={selectedQualityCategory}
                    onChange={(event) => setSelectedQualityCategory(event.target.value)}
                    maxW="180px"
                    mt={1}
                  >
                    {qualityCategories.map(category => (
                      <option key={category.key} value={category.key}>
                        {category.label}
                      </option>
                    ))}
                  </Select>
                )}
                <StatNumber color={(selectedHealth.color || 'gray') + '.500'}>
                  {activeScore}%
                </StatNumber>
                <Progress
                  value={selectedPercent}
                  colorScheme={selectedHealth.color}
                  size="sm"
                  mt={2}
                />
                {selectedCategory && (
                  <Box mt={3} fontSize="xs" color="gray.600">
                    {selectedCategory.summary && (
                      <Text mb={2}>{selectedCategory.summary}</Text>
                    )}
                    <VStack align="stretch" spacing={3}>
                      {selectedSections.map(section => (
                        <Box key={section.key} borderWidth="1px" borderColor={borderColor} borderRadius="md" p={2}>
                          <HStack justify="space-between" align="center" mb={1}>
                            <Text fontWeight="semibold">{section.label}</Text>
                            <Text>{section.score.toFixed(1)} / {section.max_score}</Text>
                          </HStack>
                          <Progress value={Math.min(100, (section.score / section.max_score) * 100)} size="xs" colorScheme={selectedHealth.color} />
                          {section.indicators && section.indicators.length > 0 && (
                            <VStack align="stretch" spacing={1} mt={2}>
                              {section.indicators.slice(0, 4).map(indicator => (
                                <Box key={section.key + '-' + indicator.label} p={1} borderRadius="sm" bg={indicatorBgColor}>
                                  <HStack justify="space-between" align="flex-start">
                                    <VStack align="flex-start" spacing={0}>
                                      <HStack spacing={2}>
                                        <Text fontSize="xs" fontWeight="semibold">{indicator.label}</Text>
                                        {indicator.status && (
                                          <Badge size="xs" colorScheme={indicatorStatusColor[indicator.status] || 'gray'}>
                                            {indicator.status.toUpperCase()}
                                          </Badge>
                                        )}
                                      </HStack>
                                      {indicator.description && (
                                        <Text fontSize="xs" color="gray.500">{indicator.description}</Text>
                                      )}
                                    </VStack>
                                    <VStack align="flex-end" spacing={0}>
                                      <Text fontSize="sm" fontWeight="semibold">{formatIndicatorValue(indicator.value, indicator.unit)}</Text>
                                      {indicator.target !== undefined && indicator.target !== null && (
                                        <Text fontSize="xs" color="gray.500">
                                          Target: {formatIndicatorValue(indicator.target, indicator.unit)}
                                        </Text>
                                      )}
                                    </VStack>
                                  </HStack>
                                </Box>
                              ))}
                              {section.indicators.length > 4 && (
                                <Text fontSize="xs" color="gray.500">
                                  +{section.indicators.length - 4} more indicators
                                </Text>
                              )}
                            </VStack>
                          )}
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                )}
                {qualityError && (
                  <Alert status="warning" variant="left-accent" mt={3} fontSize="xs">
                    <AlertIcon />
                    <Text>Unable to refresh quality overview. Showing last loaded data.</Text>
                  </Alert>
                )}
              </Stat>
              
              <Stat>
                <StatLabel>API Connection</StatLabel>
                <StatNumber color={health?.api_connected ? "green.500" : "red.500"}>
                  {health?.api_connected ? "Connected" : "Disconnected"}
                </StatNumber>
                <StatHelpText>
                  <StatArrow type={health?.api_connected ? "increase" : "decrease"} />
                  {health?.api_connected ? "All systems operational" : "Check API server"}
                </StatHelpText>
              </Stat>
              
              <Stat>
                <StatLabel>Database</StatLabel>
                <StatNumber color={health?.database_connected ? "green.500" : "red.500"}>
                  {health?.database_connected ? "Active" : "Inactive"}
                </StatNumber>
                <StatHelpText>
                  <StatArrow type={health?.database_connected ? "increase" : "decrease"} />
                  {health?.database_connected ? "Data available" : "No data found"}
                </StatHelpText>
              </Stat>
            </Grid>
          </CardBody>
        </Card>

        {/* Quick Stats */}
        <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" }} gap={6}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody textAlign="center">
              <Icon as={FaCode} boxSize={8} color="blue.500" mb={2} />
              <Stat>
                <StatNumber color="blue.500">{health?.total_nodes || 0}</StatNumber>
                <StatLabel>Total Nodes</StatLabel>
              </Stat>
            </CardBody>
          </Card>
          
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody textAlign="center">
              <Icon as={FaProjectDiagram} boxSize={8} color="green.500" mb={2} />
              <Stat>
                <StatNumber color="green.500">{health?.total_relations || 0}</StatNumber>
                <StatLabel>Relations</StatLabel>
              </Stat>
            </CardBody>
          </Card>
          
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody textAlign="center">
              <Icon as={FaGitAlt} boxSize={8} color="purple.500" mb={2} />
              <Stat>
                <StatNumber color="purple.500">{health?.recent_commits || 0}</StatNumber>
                <StatLabel>Recent Commits</StatLabel>
              </Stat>
            </CardBody>
          </Card>
          
          <Card bg={bgColor} borderColor={borderColor}>
            <CardBody textAlign="center">
              <Icon as={FaUsers} boxSize={8} color="orange.500" mb={2} />
              <Stat>
                <StatNumber color="orange.500">{health?.active_sprints || 0}</StatNumber>
                <StatLabel>Active Sprints</StatLabel>
              </Stat>
            </CardBody>
          </Card>
        </Grid>

        {/* Data Type Breakdown */}
        <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={6}>
          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <HStack>
                <Icon as={FaFileAlt} color="blue.500" />
                <Heading size="md">Node Types</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={3}>
                {nodeTypeSummary.length > 0 ? (
                  nodeTypeSummary.map((nodeType, index) => (
                    <HStack key={`node-${nodeType.type}-${index}`} justify="space-between">
                      <HStack>
                        <Box w={3} h={3} bg={`${nodeType.color}.500`} borderRadius="full" />
                        <Text fontSize="sm">{nodeType.type}</Text>
                      </HStack>
                      <Badge colorScheme={nodeType.color} variant="subtle">
                        {nodeType.count}
                      </Badge>
                    </HStack>
                  ))
                ) : (
                  <Text color="gray.500">No node type data available</Text>
                )}
              </VStack>
            </CardBody>
          </Card>

          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <HStack>
                <Icon as={FaChartLine} color="green.500" />
                <Heading size="md">Relation Types</Heading>
              </HStack>
            </CardHeader>
            <CardBody>
              <VStack align="stretch" spacing={3}>
                {relationTypeSummary.length > 0 ? (
                  relationTypeSummary.map((relationType, index) => (
                    <HStack key={`relation-${relationType.type}-${index}`} justify="space-between">
                      <HStack>
                        <Box w={3} h={3} bg={`${relationType.color}.500`} borderRadius="full" />
                        <Text fontSize="sm">{relationType.type}</Text>
                      </HStack>
                      <Badge colorScheme={relationType.color} variant="subtle">
                        {relationType.count}
                      </Badge>
                    </HStack>
                  ))
                ) : (
                  <Text color="gray.500">No relation type data available</Text>
                )}
              </VStack>
            </CardBody>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        {health?.performance_metrics && (
          <Card bg={bgColor} borderColor={borderColor}>
            <CardHeader>
              <Heading size="md">Performance Metrics</Heading>
            </CardHeader>
            <CardBody>
              <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={6}>
                <Stat>
                  <StatLabel>Avg Query Time</StatLabel>
                  <StatNumber color="blue.500">
                    {health.performance_metrics.avg_query_time_ms}ms
                  </StatNumber>
                </Stat>
                
                <Stat>
                  <StatLabel>Cache Hit Rate</StatLabel>
                  <StatNumber color="green.500">
                    {Math.round(health.performance_metrics.cache_hit_rate * 100)}%
                  </StatNumber>
                </Stat>
                
                <Stat>
                  <StatLabel>Memory Usage</StatLabel>
                  <StatNumber color="purple.500">
                    {health.performance_metrics.memory_usage_mb}MB
                  </StatNumber>
                </Stat>
              </Grid>
            </CardBody>
          </Card>
        )}

        {/* Navigation to Advanced Features */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <Heading size="md">Explore Your Codebase</Heading>
          </CardHeader>
          <CardBody>
            <Grid templateColumns={{ base: "1fr", md: "repeat(2, 1fr)" }} gap={6}>
              <VStack align="stretch" spacing={4}>
                <Box>
                  <HStack mb={2}>
                    <Icon as={FaClock} color="blue.500" />
                    <Heading size="sm">Timeline Evolution</Heading>
                  </HStack>
                  <Text fontSize="sm" color="gray.600" mb={3}>
                    Watch your codebase evolve like a living organism. Commits as generations, 
                    files as organisms, branches as lineages.
                  </Text>
                  <HStack spacing={2} flexWrap="wrap">
                    <Button as={ChakraLink} href="/dev-graph/timeline/svg" colorScheme="purple" size="sm">
                      SVG Timeline
                    </Button>
                    <Button as={ChakraLink} href="/dev-graph/timeline/webgl" colorScheme="teal" size="sm">
                      WebGL2 Timeline
                    </Button>
                    <Button as={ChakraLink} href="/dev-graph/timeline" variant="outline" size="sm">
                      Compare Modes
                    </Button>
                  </HStack>
                </Box>
              </VStack>
              
              <VStack align="stretch" spacing={4}>
                <Box>
                  <HStack mb={2}>
                    <Icon as={FaProjectDiagram} color="green.500" />
                    <Heading size="sm">Structure Analysis</Heading>
                  </HStack>
                  <Text fontSize="sm" color="gray.600" mb={3}>
                    Analyze relationships and dependencies. Discover clusters, 
                    identify critical components, and map architectural patterns.
                  </Text>
                  <Button as={ChakraLink} href="/dev-graph/structure" colorScheme="green" size="sm">
                    Explore Structure
                  </Button>
                </Box>
              </VStack>
            </Grid>
          </CardBody>
        </Card>

        {/* Quick Actions */}
        <Card bg={bgColor} borderColor={borderColor}>
          <CardHeader>
            <Heading size="md">Quick Actions</Heading>
          </CardHeader>
          <CardBody>
            <HStack spacing={4} wrap="wrap">
              <Button as={ChakraLink} href="/dev-graph/enhanced" variant="outline" size="sm">
                Enhanced Dashboard
              </Button>
              <Button as={ChakraLink} href="/dev-graph/complex" variant="outline" size="sm">
                Complex View
              </Button>
              <Button 
                onClick={() => window.open(`${DEV_GRAPH_API_URL}/docs`, '_blank')} 
                variant="outline" 
                size="sm"
              >
                API Documentation
              </Button>
            </HStack>
          </CardBody>
        </Card>
      </VStack>
    </Box>
  );
}
