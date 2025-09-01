'use client';

import { Box, Text, VStack, HStack, Badge } from '@chakra-ui/react';

export function TemporalAnalytics({ events, nodes, relations }: { events: any[]; nodes: any[]; relations: any[] }) {
  const totalCommits = events.length;
  const totalNodes = nodes.length;
  const totalRelations = relations.length;
  const types = new Map<string, number>();
  for (const r of relations) {
    types.set(r.type, (types.get(r.type) || 0) + 1);
  }
  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <Text fontWeight="bold" mb={2}>Temporal Analytics</Text>
      <VStack align="start" spacing={2}>
        <Text fontSize="sm">Commits: {totalCommits}</Text>
        <Text fontSize="sm">Nodes: {totalNodes}</Text>
        <Text fontSize="sm">Relations: {totalRelations}</Text>
        <HStack spacing={2} flexWrap="wrap">
          {Array.from(types.entries()).map(([t, c]) => (
            <Badge key={t} colorScheme="blue">{t}: {c}</Badge>
          ))}
        </HStack>
      </VStack>
    </Box>
  );
}

export default TemporalAnalytics;

'use client';

import { Box, VStack, HStack, Text, Stat, StatLabel, StatNumber, StatHelpText, StatArrow, useColorModeValue, SimpleGrid, Progress, Badge } from '@chakra-ui/react';
import { useMemo } from 'react';
import { FiTrendingUp, FiTrendingDown, FiClock, FiUsers, FiGitCommit, FiFile } from 'react-icons/fi';

export interface TemporalMetrics {
  totalEvents: number;
  timeSpan: {
    start: string;
    end: string;
    duration: number; // in days
  };
  activityMetrics: {
    commitsPerDay: number;
    filesChangedPerDay: number;
    authorsPerDay: number;
    peakActivityDay: string;
    peakActivityCount: number;
  };
  evolutionMetrics: {
    requirementsEvolved: number;
    filesRefactored: number;
    dependenciesChanged: number;
    evolutionRate: number; // percentage
  };
  trends: {
    commitTrend: 'increasing' | 'decreasing' | 'stable';
    complexityTrend: 'increasing' | 'decreasing' | 'stable';
    teamActivityTrend: 'increasing' | 'decreasing' | 'stable';
  };
}

export interface TemporalAnalyticsProps {
  events: Array<{
    id: string;
    timestamp: string;
    type: string;
    author?: string;
    files_changed?: string[];
  }>;
  nodes: Array<{
    id: string;
    type: string;
    created_at?: string;
    updated_at?: string;
  }>;
  relations: Array<{
    from: string;
    to: string;
    type: string;
    created_at?: string;
  }>;
}

export function TemporalAnalytics({ events, nodes, relations }: TemporalAnalyticsProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const accentColor = useColorModeValue('green.500', 'green.400');

  const metrics = useMemo(() => {
    if (!events.length) return null;

    const sortedEvents = [...events].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const startDate = new Date(sortedEvents[0].timestamp);
    const endDate = new Date(sortedEvents[sortedEvents.length - 1].timestamp);
    const duration = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));

    // Activity per day
    const activityByDay = new Map<string, number>();
    const filesByDay = new Map<string, number>();
    const authorsByDay = new Map<string, Set<string>>();

    events.forEach(event => {
      const day = new Date(event.timestamp).toDateString();
      activityByDay.set(day, (activityByDay.get(day) || 0) + 1);
      
      if (event.files_changed) {
        filesByDay.set(day, (filesByDay.get(day) || 0) + event.files_changed.length);
      }
      
      if (event.author) {
        if (!authorsByDay.has(day)) {
          authorsByDay.set(day, new Set());
        }
        authorsByDay.get(day)!.add(event.author);
      }
    });

    const commitsPerDay = events.length / duration;
    const filesChangedPerDay = events.reduce((sum, e) => sum + (e.files_changed?.length || 0), 0) / duration;
    const authorsPerDay = Array.from(authorsByDay.values()).reduce((sum, authors) => sum + authors.size, 0) / duration;

    // Find peak activity day
    let peakActivityDay = '';
    let peakActivityCount = 0;
    activityByDay.forEach((count, day) => {
      if (count > peakActivityCount) {
        peakActivityCount = count;
        peakActivityDay = day;
      }
    });

    // Evolution metrics
    const requirementsEvolved = relations.filter(r => r.type === 'EVOLVES_FROM').length;
    const filesRefactored = relations.filter(r => r.type === 'REFACTORED_TO').length;
    const dependenciesChanged = relations.filter(r => r.type === 'DEPENDS_ON').length;
    const evolutionRate = (requirementsEvolved + filesRefactored) / nodes.length * 100;

    // Trends (simplified calculation)
    const midPoint = Math.floor(events.length / 2);
    const firstHalf = events.slice(0, midPoint).length;
    const secondHalf = events.slice(midPoint).length;
    
    const commitTrend = secondHalf > firstHalf ? 'increasing' : secondHalf < firstHalf ? 'decreasing' : 'stable';
    const complexityTrend = nodes.length > events.length / 2 ? 'increasing' : 'decreasing';
    const teamActivityTrend = authorsByDay.size > duration / 2 ? 'increasing' : 'decreasing';

    return {
      totalEvents: events.length,
      timeSpan: {
        start: startDate.toLocaleDateString(),
        end: endDate.toLocaleDateString(),
        duration,
      },
      activityMetrics: {
        commitsPerDay: Math.round(commitsPerDay * 100) / 100,
        filesChangedPerDay: Math.round(filesChangedPerDay * 100) / 100,
        authorsPerDay: Math.round(authorsPerDay * 100) / 100,
        peakActivityDay,
        peakActivityCount,
      },
      evolutionMetrics: {
        requirementsEvolved,
        filesRefactored,
        dependenciesChanged,
        evolutionRate: Math.round(evolutionRate * 100) / 100,
      },
      trends: {
        commitTrend,
        complexityTrend,
        teamActivityTrend,
      },
    };
  }, [events, nodes, relations]);

  if (!metrics) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
        <Text color="gray.500">No temporal data available for analysis</Text>
      </Box>
    );
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return <StatArrow type="increase" color="green.500" />;
      case 'decreasing':
        return <StatArrow type="decrease" color="red.500" />;
      default:
        return <StatArrow type="decrease" color="gray.500" />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing':
        return 'green';
      case 'decreasing':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
      <VStack spacing={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="lg" fontWeight="bold" mb={2}>Temporal Analytics</Text>
          <Text fontSize="sm" color="gray.500">
            Analysis of development activity over {metrics.timeSpan.duration} days
          </Text>
        </Box>

        {/* Time Span Overview */}
        <Box p={4} bg={`${accentColor}10`} borderRadius="md">
          <HStack justify="space-between" align="center">
            <VStack align="start" spacing={1}>
              <Text fontSize="sm" fontWeight="medium">Time Period</Text>
              <Text fontSize="lg">
                {metrics.timeSpan.start} → {metrics.timeSpan.end}
              </Text>
            </VStack>
            <VStack align="end" spacing={1}>
              <Text fontSize="sm" color="gray.500">Duration</Text>
              <Text fontSize="lg" fontWeight="bold">
                {metrics.timeSpan.duration} days
              </Text>
            </VStack>
          </HStack>
        </Box>

        {/* Activity Metrics */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Activity Metrics</Text>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
            <Stat>
              <StatLabel>Commits/Day</StatLabel>
              <StatNumber>{metrics.activityMetrics.commitsPerDay}</StatNumber>
              <StatHelpText>
                <FiGitCommit style={{ display: 'inline', marginRight: '4px' }} />
                Average daily commits
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Files Changed/Day</StatLabel>
              <StatNumber>{metrics.activityMetrics.filesChangedPerDay}</StatNumber>
              <StatHelpText>
                <FiFile style={{ display: 'inline', marginRight: '4px' }} />
                Average daily file changes
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Authors/Day</StatLabel>
              <StatNumber>{metrics.activityMetrics.authorsPerDay}</StatNumber>
              <StatHelpText>
                <FiUsers style={{ display: 'inline', marginRight: '4px' }} />
                Average daily contributors
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Peak Activity</StatLabel>
              <StatNumber>{metrics.activityMetrics.peakActivityCount}</StatNumber>
              <StatHelpText>
                <FiClock style={{ display: 'inline', marginRight: '4px' }} />
                {metrics.activityMetrics.peakActivityDay}
              </StatHelpText>
            </Stat>
          </SimpleGrid>
        </Box>

        {/* Evolution Metrics */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Evolution Metrics</Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <Box p={4} borderWidth={1} borderColor={borderColor} borderRadius="md">
              <VStack spacing={3} align="stretch">
                <HStack justify="space-between">
                  <Text fontSize="sm">Requirements Evolution</Text>
                  <Badge colorScheme="blue">{metrics.evolutionMetrics.requirementsEvolved}</Badge>
                </HStack>
                <HStack justify="space-between">
                  <Text fontSize="sm">Files Refactored</Text>
                  <Badge colorScheme="orange">{metrics.evolutionMetrics.filesRefactored}</Badge>
                </HStack>
                <HStack justify="space-between">
                  <Text fontSize="sm">Dependencies Changed</Text>
                  <Badge colorScheme="purple">{metrics.evolutionMetrics.dependenciesChanged}</Badge>
                </HStack>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth={1} borderColor={borderColor} borderRadius="md">
              <VStack spacing={3} align="stretch">
                <Text fontSize="sm">Evolution Rate</Text>
                <Progress 
                  value={Math.min(metrics.evolutionMetrics.evolutionRate, 100)} 
                  colorScheme="green" 
                  size="lg"
                />
                <Text fontSize="lg" fontWeight="bold">
                  {metrics.evolutionMetrics.evolutionRate}%
                </Text>
                <Text fontSize="xs" color="gray.500">
                  of nodes have evolved over time
                </Text>
              </VStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Trends */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Development Trends</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Box p={4} borderWidth={1} borderColor={borderColor} borderRadius="md">
              <HStack justify="space-between" align="center">
                <VStack align="start" spacing={1}>
                  <Text fontSize="sm">Commit Activity</Text>
                  <Text fontSize="lg" fontWeight="bold">
                    {metrics.trends.commitTrend.charAt(0).toUpperCase() + metrics.trends.commitTrend.slice(1)}
                  </Text>
                </VStack>
                {getTrendIcon(metrics.trends.commitTrend)}
              </HStack>
              <Badge colorScheme={getTrendColor(metrics.trends.commitTrend)} mt={2}>
                {metrics.trends.commitTrend === 'increasing' ? <FiTrendingUp /> : <FiTrendingDown />}
              </Badge>
            </Box>
            
            <Box p={4} borderWidth={1} borderColor={borderColor} borderRadius="md">
              <HStack justify="space-between" align="center">
                <VStack align="start" spacing={1}>
                  <Text fontSize="sm">Code Complexity</Text>
                  <Text fontSize="lg" fontWeight="bold">
                    {metrics.trends.complexityTrend.charAt(0).toUpperCase() + metrics.trends.complexityTrend.slice(1)}
                  </Text>
                </VStack>
                {getTrendIcon(metrics.trends.complexityTrend)}
              </HStack>
              <Badge colorScheme={getTrendColor(metrics.trends.complexityTrend)} mt={2}>
                {metrics.trends.complexityTrend === 'increasing' ? <FiTrendingUp /> : <FiTrendingDown />}
              </Badge>
            </Box>
            
            <Box p={4} borderWidth={1} borderColor={borderColor} borderRadius="md">
              <HStack justify="space-between" align="center">
                <VStack align="start" spacing={1}>
                  <Text fontSize="sm">Team Activity</Text>
                  <Text fontSize="lg" fontWeight="bold">
                    {metrics.trends.teamActivityTrend.charAt(0).toUpperCase() + metrics.trends.teamActivityTrend.slice(1)}
                  </Text>
                </VStack>
                {getTrendIcon(metrics.trends.teamActivityTrend)}
              </HStack>
              <Badge colorScheme={getTrendColor(metrics.trends.teamActivityTrend)} mt={2}>
                {metrics.trends.teamActivityTrend === 'increasing' ? <FiTrendingUp /> : <FiTrendingDown />}
              </Badge>
            </Box>
          </SimpleGrid>
        </Box>
      </VStack>
    </Box>
  );
}
