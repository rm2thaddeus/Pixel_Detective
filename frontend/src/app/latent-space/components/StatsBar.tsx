import { HStack, Stat, StatLabel, StatNumber } from '@chakra-ui/react';
import React from 'react';
import { UMAPProjectionResponse } from '../types/latent-space';

interface StatsBarProps {
  stats: UMAPProjectionResponse['clustering_info'];
  totalPoints: number;
}

export const StatsBar: React.FC<StatsBarProps> = ({ stats, totalPoints }) => {
  // Helper to render a metric stat
  const Metric = ({ label, value }: { label: string | number; value: string | number }) => (
  <Stat minW="80px" textAlign="center">
    <StatLabel fontSize="xs">{label}</StatLabel>
    <StatNumber fontSize="md">{value}</StatNumber>
  </Stat>
);

return (
  <HStack
    spacing={6}
    align="center"
    w="full"
    px={2}
    py={1}
    borderRadius="md"
    bg="gray.50"
    _dark={{ bg: 'gray.700' }}
    overflowX="auto"
  >
    {/* Metrics */}
    <Metric label="Clusters" value={stats?.n_clusters ?? '-'} />
    <Metric label="Outliers" value={stats?.n_outliers ?? 0} />
    {stats?.silhouette_score && (
      <Metric
        label="Silhouette"
        value={stats.silhouette_score.toFixed(2)}
      />
    )}
    <Metric label="Points" value={totalPoints} />
  </HStack>
);
}; 