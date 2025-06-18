'use client';

import React from 'react';
import {
  VStack,
  HStack,
  Text,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Badge,
  Progress,
  Divider,
  SimpleGrid,
  useColorModeValue,
} from '@chakra-ui/react';
import { ClusteringInfo } from '../types/latent-space';

interface MetricsPanelProps {
  clusteringInfo: ClusteringInfo | null;
  totalPoints: number;
  loadingTime?: number;
}

export function MetricsPanel({ 
  clusteringInfo, 
  totalPoints, 
  loadingTime 
}: MetricsPanelProps) {
  const cardBg = useColorModeValue('white', 'gray.800');
  const statBg = useColorModeValue('gray.50', 'gray.700');

  if (!clusteringInfo) {
    return (
      <Card bg={cardBg}>
        <CardHeader>
          <Heading size="md">Clustering Metrics</Heading>
        </CardHeader>
        <CardBody>
          <Text color="gray.500">No clustering data available</Text>
        </CardBody>
      </Card>
    );
  }

  const getQualityColor = (score?: number) => {
    if (!score) return 'gray';
    if (score > 0.7) return 'green';
    if (score > 0.5) return 'yellow';
    return 'red';
  };

  const getQualityLabel = (score?: number) => {
    if (!score) return 'N/A';
    if (score > 0.7) return 'Excellent';
    if (score > 0.5) return 'Good';
    if (score > 0.3) return 'Fair';
    return 'Poor';
  };

  return (
    <Card bg={cardBg}>
      <CardHeader>
        <HStack justify="space-between" align="center">
          <Heading size="md">Clustering Metrics</Heading>
          <Badge colorScheme="blue" variant="subtle">
            {clusteringInfo.algorithm}
          </Badge>
        </HStack>
      </CardHeader>
      <CardBody>
        <VStack spacing={6} align="stretch">
          {/* Cluster Overview */}
          <SimpleGrid columns={2} spacing={4}>
            <Stat bg={statBg} p={3} borderRadius="md">
              <StatLabel>Total Clusters</StatLabel>
              <StatNumber>{clusteringInfo.n_clusters}</StatNumber>
            </Stat>
            <Stat bg={statBg} p={3} borderRadius="md">
              <StatLabel>Outliers</StatLabel>
              <StatNumber>{clusteringInfo.n_outliers || 0}</StatNumber>
              <StatHelpText>
                {((clusteringInfo.n_outliers || 0) / totalPoints * 100).toFixed(1)}%
              </StatHelpText>
            </Stat>
          </SimpleGrid>

          {/* Quality Metrics */}
          {clusteringInfo.silhouette_score && (
            <>
              <Divider />
              <VStack spacing={3} align="stretch">
                <Text fontWeight="semibold">Clustering Quality</Text>
                <HStack justify="space-between">
                  <Text fontSize="sm">Silhouette Score</Text>
                  <Badge colorScheme={getQualityColor(clusteringInfo.silhouette_score)}>
                    {getQualityLabel(clusteringInfo.silhouette_score)}
                  </Badge>
                </HStack>
                <Progress
                  value={clusteringInfo.silhouette_score * 100}
                  colorScheme={getQualityColor(clusteringInfo.silhouette_score)}
                  size="lg"
                />
                <Text fontSize="sm" color="gray.600">
                  Score: {clusteringInfo.silhouette_score.toFixed(3)}
                </Text>
              </VStack>
            </>
          )}

          {/* Algorithm Parameters */}
          <Divider />
          <VStack spacing={2} align="stretch">
            <Text fontWeight="semibold">Parameters</Text>
            {Object.entries(clusteringInfo.parameters).map(([key, value]) => (
              <HStack key={key} justify="space-between">
                <Text fontSize="sm" color="gray.600">{key}:</Text>
                <Text fontSize="sm">{value}</Text>
              </HStack>
            ))}
          </VStack>

          {/* Performance */}
          {loadingTime && (
            <>
              <Divider />
              <Stat bg={statBg} p={3} borderRadius="md">
                <StatLabel>Processing Time</StatLabel>
                <StatNumber>{loadingTime.toFixed(0)}ms</StatNumber>
                <StatHelpText>
                  {totalPoints} points processed
                </StatHelpText>
              </Stat>
            </>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
} 