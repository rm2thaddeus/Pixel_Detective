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

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'ok':
        return successColor;
      case 'warning':
        return warningColor;
      case 'error':
      case 'critical':
        return errorColor;
      default:
        return 'gray.500';
    }
  };

  const getStatusBadge = (status: string) => {
    const color = getStatusColor(status);
    return (
      <Badge colorScheme={status.toLowerCase() === 'healthy' || status.toLowerCase() === 'ok' ? 'green' : 
                           status.toLowerCase() === 'warning' ? 'orange' : 'red'} 
             variant="subtle" size="sm">
        {status}
      </Badge>
    );
  };

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" className={className}>
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Text fontSize="md" fontWeight="bold">System Status</Text>
          {getStatusBadge(telemetry.status || 'Unknown')}
        </HStack>

        {/* Health Metrics */}
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
          <Stat size="sm">
            <StatLabel fontSize="xs">Uptime</StatLabel>
            <StatNumber fontSize="sm">{telemetry.uptime || 'N/A'}</StatNumber>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Memory</StatLabel>
            <StatNumber fontSize="sm">{telemetry.memory_usage || 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">{telemetry.memory_percent || '0'}% used</StatHelpText>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">CPU</StatLabel>
            <StatNumber fontSize="sm">{telemetry.cpu_usage || 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">{telemetry.cpu_percent || '0'}% used</StatHelpText>
          </Stat>
          <Stat size="sm">
            <StatLabel fontSize="xs">Response Time</StatLabel>
            <StatNumber fontSize="sm">{telemetry.avg_response_time || 'N/A'}</StatNumber>
            <StatHelpText fontSize="xs">ms</StatHelpText>
          </Stat>
        </SimpleGrid>

        {/* Database Status */}
        {telemetry.database && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={2}>Database</Text>
            <HStack spacing={4}>
              <HStack spacing={1}>
                <Text fontSize="xs" color="gray.600">Status:</Text>
                {getStatusBadge(telemetry.database.status || 'Unknown')}
              </HStack>
              <HStack spacing={1}>
                <Text fontSize="xs" color="gray.600">Connections:</Text>
                <Text fontSize="xs">{telemetry.database.connections || 'N/A'}</Text>
              </HStack>
              <HStack spacing={1}>
                <Text fontSize="xs" color="gray.600">Size:</Text>
                <Text fontSize="xs">{telemetry.database.size || 'N/A'}</Text>
              </HStack>
            </HStack>
          </Box>
        )}

        {/* Services Status */}
        {telemetry.services && Object.keys(telemetry.services).length > 0 && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={2}>Services</Text>
            <VStack spacing={1} align="stretch">
              {Object.entries(telemetry.services).map(([service, status]) => (
                <HStack key={service} justify="space-between" fontSize="xs">
                  <Text textTransform="capitalize">{service.replace('_', ' ')}</Text>
                  {getStatusBadge(typeof status === 'string' ? status : 'Unknown')}
                </HStack>
              ))}
            </VStack>
          </Box>
        )}

        {/* Performance Metrics */}
        {telemetry.performance && (
          <Box>
            <Text fontSize="sm" fontWeight="medium" mb={2}>Performance</Text>
            <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
              <Stat size="sm">
                <StatLabel fontSize="xs">Requests/min</StatLabel>
                <StatNumber fontSize="sm">{telemetry.performance.requests_per_minute || 'N/A'}</StatNumber>
              </Stat>
              <Stat size="sm">
                <StatLabel fontSize="xs">Error Rate</StatLabel>
                <StatNumber fontSize="sm">{telemetry.performance.error_rate || 'N/A'}</StatNumber>
                <StatHelpText fontSize="xs">%</StatHelpText>
              </Stat>
              <Stat size="sm">
                <StatLabel fontSize="xs">Cache Hit</StatLabel>
                <StatNumber fontSize="sm">{telemetry.performance.cache_hit_rate || 'N/A'}</StatNumber>
                <StatHelpText fontSize="xs">%</StatHelpText>
              </Stat>
            </SimpleGrid>
          </Box>
        )}

        {/* Last Updated */}
        <Text fontSize="xs" color="gray.500" textAlign="right">
          Last updated: {telemetry.timestamp ? new Date(telemetry.timestamp).toLocaleTimeString() : 'Unknown'}
        </Text>
      </VStack>
    </Box>
  );
}

export default TelemetryDisplay;
