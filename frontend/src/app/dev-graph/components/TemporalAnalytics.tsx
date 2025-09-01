'use client';

import { Box, VStack, HStack, Text, Stat, StatLabel, StatNumber, StatHelpText, StatArrow, useColorModeValue, SimpleGrid, Progress, Badge, Icon } from '@chakra-ui/react';
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

    // Calculate daily activity
    const dailyActivity = new Map<string, number>();
    const dailyFiles = new Map<string, number>();
    const dailyAuthors = new Map<string, Set<string>>();

    events.forEach(event => {
      const date = event.timestamp.split('T')[0];
      dailyActivity.set(date, (dailyActivity.get(date) || 0) + 1);
      
      if (event.files_changed) {
        dailyFiles.set(date, (dailyFiles.get(date) || 0) + event.files_changed.length);
      }
      
      if (event.author) {
        if (!dailyAuthors.has(date)) {
          dailyAuthors.set(date, new Set());
        }
        dailyAuthors.get(date)!.add(event.author);
      }
    });

    const commitsPerDay = events.length / Math.max(duration, 1);
    const filesChangedPerDay = Array.from(dailyFiles.values()).reduce((sum, count) => sum + count, 0) / Math.max(duration, 1);
    const authorsPerDay = Array.from(dailyAuthors.values()).reduce((sum, authors) => sum + authors.size, 0) / Math.max(duration, 1);

    // Find peak activity day
    let peakActivityDay = '';
    let peakActivityCount = 0;
    dailyActivity.forEach((count, date) => {
      if (count > peakActivityCount) {
        peakActivityCount = count;
        peakActivityDay = date;
      }
    });

    // Calculate evolution metrics
    const requirementsEvolved = nodes.filter(node => 
      node.type === 'requirement' && node.updated_at && node.updated_at !== node.created_at
    ).length;

    const filesRefactored = relations.filter(rel => 
      rel.type === 'refactors' || rel.type === 'modifies'
    ).length;

    const dependenciesChanged = relations.filter(rel => 
      rel.type === 'depends_on' || rel.type === 'imports'
    ).length;

    const evolutionRate = Math.round((requirementsEvolved / Math.max(nodes.filter(n => n.type === 'requirement').length, 1)) * 100);

    // Calculate trends
    const commitTrend = commitsPerDay > 5 ? 'increasing' : commitsPerDay > 2 ? 'stable' : 'decreasing';
    const complexityTrend = filesRefactored > 10 ? 'increasing' : filesRefactored > 5 ? 'stable' : 'decreasing';
    const teamActivityTrend = authorsPerDay > 3 ? 'increasing' : authorsPerDay > 1 ? 'stable' : 'decreasing';

    return {
      totalEvents: events.length,
      timeSpan: {
        start: startDate.toISOString().split('T')[0],
        end: endDate.toISOString().split('T')[0],
        duration
      },
      activityMetrics: {
        commitsPerDay: Math.round(commitsPerDay * 100) / 100,
        filesChangedPerDay: Math.round(filesChangedPerDay * 100) / 100,
        authorsPerDay: Math.round(authorsPerDay * 100) / 100,
        peakActivityDay,
        peakActivityCount
      },
      evolutionMetrics: {
        requirementsEvolved,
        filesRefactored,
        dependenciesChanged,
        evolutionRate
      },
      trends: {
        commitTrend,
        complexityTrend,
        teamActivityTrend
      }
    };
  }, [events, nodes, relations]);

  const getTrendIcon = (trend: string) => {
    if (trend === 'increasing') {
      return <Icon as={FiTrendingUp} color="green.500" boxSize={6} />;
    } else if (trend === 'decreasing') {
      return <Icon as={FiTrendingDown} color="red.500" boxSize={6} />;
    }
    return <Icon as={FiClock} color="gray.500" boxSize={6} />;
  };

  const getTrendColor = (trend: string) => {
    if (trend === 'increasing') return 'green';
    if (trend === 'decreasing') return 'red';
    return 'gray';
  };

  if (!metrics) {
    return (
      <Box p={6} textAlign="center" bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
        <Text color="gray.500">No temporal data available</Text>
      </Box>
    );
  }

  return (
    <Box p={6} bg={bgColor} borderWidth="1" borderColor={borderColor} borderRadius="lg">
      <VStack spacing={6} align="stretch">
        <Text fontSize="xl" fontWeight="bold" color={useColorModeValue('gray.800', 'white')}>
          Temporal Analytics
        </Text>

        {/* Overview Stats */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Overview</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Stat>
              <StatLabel>Total Events</StatLabel>
              <StatNumber>{metrics.totalEvents}</StatNumber>
              <StatHelpText>
                <StatArrow type="increase" />
                {metrics.activityMetrics.commitsPerDay} per day
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Time Span</StatLabel>
              <StatNumber>{metrics.timeSpan.duration}</StatNumber>
              <StatHelpText>
                {metrics.timeSpan.start} to {metrics.timeSpan.end}
              </StatHelpText>
            </Stat>
            
            <Stat>
              <StatLabel>Peak Activity</StatLabel>
              <StatNumber>{metrics.activityMetrics.peakActivityCount}</StatNumber>
              <StatHelpText>
                on {metrics.activityMetrics.peakActivityDay}
              </StatHelpText>
            </Stat>
          </SimpleGrid>
        </Box>

        {/* Activity Metrics */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Daily Activity</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
              <VStack spacing={2}>
                <Icon as={FiGitCommit} color={accentColor} boxSize={6} />
                <Text fontSize="lg" fontWeight="bold">{metrics.activityMetrics.commitsPerDay}</Text>
                <Text fontSize="sm" color="gray.500">Commits per day</Text>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
              <VStack spacing={2}>
                <Icon as={FiFile} color={accentColor} boxSize={6} />
                <Text fontSize="lg" fontWeight="bold">{metrics.activityMetrics.filesChangedPerDay}</Text>
                <Text fontSize="sm" color="gray.500">Files changed per day</Text>
              </VStack>
            </Box>
            
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
              <VStack spacing={2}>
                <Icon as={FiUsers} color={accentColor} boxSize={6} />
                <Text fontSize="lg" fontWeight="bold">{metrics.activityMetrics.authorsPerDay}</Text>
                <Text fontSize="sm" color="gray.500">Authors per day</Text>
              </VStack>
            </Box>
          </SimpleGrid>
        </Box>

        {/* Evolution Metrics */}
        <Box>
          <Text fontSize="md" fontWeight="medium" mb={3}>Evolution Metrics</Text>
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
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
            
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
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
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
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
                {metrics.trends.commitTrend === 'increasing' ? <Icon as={FiTrendingUp} /> : <Icon as={FiTrendingDown} />}
              </Badge>
            </Box>
            
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
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
                {metrics.trends.complexityTrend === 'increasing' ? <Icon as={FiTrendingUp} /> : <Icon as={FiTrendingDown} />}
              </Badge>
            </Box>
            
            <Box p={4} borderWidth="1" borderColor={borderColor} borderRadius="md">
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
                {metrics.trends.teamActivityTrend === 'increasing' ? <Icon as={FiTrendingUp} /> : <Icon as={FiTrendingDown} />}
              </Badge>
            </Box>
          </SimpleGrid>
        </Box>
      </VStack>
    </Box>
  );
}

export default TemporalAnalytics;
