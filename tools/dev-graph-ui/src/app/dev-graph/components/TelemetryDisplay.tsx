'use client';

import { Box, VStack, HStack, Text, Badge, useColorModeValue, Alert, AlertIcon, Spinner, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText } from '@chakra-ui/react';
import { useTelemetry } from '../hooks/useWindowedSubgraph';

export interface TelemetryDisplayProps {
  className?: string;
}

export function TelemetryDisplay({ className }: TelemetryDisplayProps) {
  const { data: telemetry, isLoading, error } = useTelemetry();
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const successColor = useColorModeValue('green.500', 'green.400');
  const warningColor = useColorModeValue('orange.500', 'orange.400');
  const errorColor = useColorModeValue('red.500', 'red.400');

  if (isLoading) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" className={className}>
        <HStack justify="center">
          <Spinner size="sm" />
          <Text fontSize="sm">Loading system status...</Text>
        </HStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" className={className}>
        <Alert status="error" size="sm">
          <AlertIcon />
          <Text fontSize="sm">Failed to load system status</Text>
        </Alert>
      </Box>
    );
  }

  if (!telemetry) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" className={className}>
        <Text fontSize="sm" color="gray.500">No telemetry data available</Text>
      </Box>
    );
  }

  // Derive a simple status from metrics
  const derivedStatus = (() => {
    // If cache_hit_rate and avg_query_time_ms present, infer status
    const hit = typeof (telemetry as any).cache_hit_rate === 'number' ? (telemetry as any).cache_hit_rate : 0;
    const avg = typeof (telemetry as any).avg_query_time_ms === 'number' ? (telemetry as any).avg_query_time_ms : 0;
    if (avg > 0 && hit >= 0) return 'OK';
    return 'Unknown';
  })();

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" className={className}>
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Text fontSize="md" fontWeight="bold">Engine Telemetry</Text>
          <Badge colorScheme={derivedStatus === 'OK' ? 'green' : 'gray'} variant="subtle" size="sm">
            {derivedStatus}
          </Badge>
        </HStack>

        {/* Health Metrics */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Stat size="sm">
            <StatLabel fontSize="xs">Avg Query Time</StatLabel>
            <StatNumber fontSize="sm">{(telemetry as any).avg_query_time_ms ?? 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">ms</StatHelpText>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Cache Hit Rate</StatLabel>
            <StatNumber fontSize="sm">{Math.round(((telemetry as any).cache_hit_rate ?? 0) * 100)}</StatNumber>
            <StatHelpText fontSize="xs">%</StatHelpText>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Cache Size</StatLabel>
            <StatNumber fontSize="sm">{(telemetry as any).cache_size ?? 'N/A'}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Memory</StatLabel>
            <StatNumber fontSize="sm">{(telemetry as any).memory_usage_mb ?? 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">MB</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Uptime and connections if available */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Stat size="sm">
            <StatLabel fontSize="xs">Uptime</StatLabel>
            <StatNumber fontSize="sm">{(telemetry as any).uptime_seconds ?? 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">seconds</StatHelpText>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Active Connections</StatLabel>
            <StatNumber fontSize="sm">{(telemetry as any).active_connections ?? 'N/A'}</StatNumber>
          </Stat>
        </SimpleGrid>
      </VStack>
    </Box>
  );
}

export default TelemetryDisplay;
