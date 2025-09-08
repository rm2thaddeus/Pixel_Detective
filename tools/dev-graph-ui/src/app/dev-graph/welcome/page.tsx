'use client';
import { Box, Heading, Text, VStack, HStack, Grid, GridItem, Card, CardBody, CardHeader, Badge, Button, Spinner, Alert, AlertIcon, useColorModeValue, Stat, StatLabel, StatNumber, StatHelpText, StatArrow, Progress, Divider, Icon, Flex } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { Link as ChakraLink } from '@chakra-ui/react';
import { FaCode, FaGitAlt, FaFileAlt, FaProjectDiagram, FaClock, FaUsers, FaChartLine, FaExclamationTriangle, FaCheckCircle, FaTimesCircle } from 'react-icons/fa';
import { useAnalytics, useTelemetry, useWindowedSubgraph } from '../hooks/useWindowedSubgraph';
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

export default function WelcomeDashboard() {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const pageBgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBgColor = useColorModeValue('gray.50', 'gray.700');

  // Use new hooks for data fetching
  const { data: analyticsData, isLoading: analyticsLoading, error: analyticsError } = useAnalytics();
  const { data: telemetryData, isLoading: telemetryLoading, error: telemetryError } = useTelemetry();
  const { data: subgraphData, isLoading: subgraphLoading, error: subgraphError } = useWindowedSubgraph({ limit: 10 });
  
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
  const loading = analyticsLoading || telemetryLoading || subgraphLoading || commitsLoading || sprintsLoading;
  const error = analyticsError || telemetryError || subgraphError;

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

  // Helper function to calculate data quality score
  const calculateDataQualityScore = (analytics: any, commits: any) => {
    let score = 0;
    
    // Base score for having data
    if (analytics?.activity?.peak_activity?.count > 0) score += 20;
    if (analytics?.activity?.files_changed_per_day > 0) score += 20;
    if (analytics?.activity?.authors_per_day > 0) score += 10;
    
    // Bonus for recent activity
    if (Array.isArray(commits) && commits.length > 0) {
      score += 20;
      // Check for recent commits (last 7 days)
      const recentCommits = commits.filter((c: any) => {
        const commitDate = new Date(c.timestamp);
        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        return commitDate > weekAgo;
      });
      if (recentCommits.length > 0) score += 10;
    }
    
    // Bonus for data diversity
    if (analytics?.activity?.authors_per_day > 1) score += 10;
    if (analytics?.activity?.files_changed_per_day > 100) score += 10;
    
    // Bonus for graph complexity
    if (analytics?.graph?.total_nodes > 1000) score += 10;
    if (analytics?.graph?.total_edges > 10000) score += 10;
    
    return Math.min(100, score);
  };

  // Process data into SystemHealth format
  const health: SystemHealth | null = analyticsData && telemetryData ? {
    api_connected: true, // If we got data, API is connected
    database_connected: true, // If we got data, database is connected
    last_ingestion: new Date().toISOString(),
    data_quality_score: calculateDataQualityScore(analyticsData, commitsData),
    total_nodes: analyticsData.graph.total_nodes || 0,
    total_relations: analyticsData.graph.total_edges || 0,
    recent_commits: analyticsData.activity.peak_activity.count || 0,
    active_sprints: Array.isArray(sprintsData) ? sprintsData.length : 0,
    node_types: Object.entries(analyticsData.graph.node_types || {}).map(([type, count]) => ({
      type,
      count: count as number,
      color: getNodeTypeColor(type)
    })),
    relation_types: Object.entries(analyticsData.graph.edge_types || {})
      .map(([type, count]) => ({
        type,
        count: count as number,
        color: getRelationTypeColor(type)
      }))
      .sort((a, b) => b.count - a.count), // Sort by count descending
    performance_metrics: {
      avg_query_time_ms: telemetryData.avg_query_time_ms || 0,
      cache_hit_rate: telemetryData.cache_hit_rate || 0,
      memory_usage_mb: telemetryData.memory_usage_mb || 0
    }
  } : null;

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

  const healthStatus = health ? getHealthStatus(health.data_quality_score) : { status: 'unknown', color: 'gray', icon: FaTimesCircle };

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
              <Icon as={healthStatus.icon} color={`${healthStatus.color}.500`} />
              <Heading size="md">System Health</Heading>
              <Badge colorScheme={healthStatus.color} ml="auto">
                {healthStatus.status.toUpperCase()}
              </Badge>
            </HStack>
          </CardHeader>
          <CardBody>
            <Grid templateColumns={{ base: "1fr", md: "repeat(3, 1fr)" }} gap={6}>
              <Stat>
                <StatLabel>Data Quality Score</StatLabel>
                <StatNumber color={`${healthStatus.color}.500`}>
                  {health?.data_quality_score || 0}%
                </StatNumber>
                <Progress 
                  value={health?.data_quality_score || 0} 
                  colorScheme={healthStatus.color}
                  size="sm"
                  mt={2}
                />
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
                {health?.node_types?.slice(0, 6).map((nodeType, index) => (
                  <HStack key={`node-${nodeType.type}-${index}`} justify="space-between">
                    <HStack>
                      <Box w={3} h={3} bg={`${nodeType.color}.500`} borderRadius="full" />
                      <Text fontSize="sm">{nodeType.type}</Text>
                    </HStack>
                    <Badge colorScheme={nodeType.color} variant="subtle">
                      {nodeType.count}
                    </Badge>
                  </HStack>
                )) || <Text color="gray.500">No node type data available</Text>}
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
                {health?.relation_types?.slice(0, 6).map((relationType, index) => (
                  <HStack key={`relation-${relationType.type}-${index}`} justify="space-between">
                    <HStack>
                      <Box w={3} h={3} bg={`${relationType.color}.500`} borderRadius="full" />
                      <Text fontSize="sm">{relationType.type}</Text>
                    </HStack>
                    <Badge colorScheme={relationType.color} variant="subtle">
                      {relationType.count}
                    </Badge>
                  </HStack>
                )) || <Text color="gray.500">No relation type data available</Text>}
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
                  <Button as={ChakraLink} href="/dev-graph/timeline" colorScheme="blue" size="sm">
                    Explore Timeline
                  </Button>
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
