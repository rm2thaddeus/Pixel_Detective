import React from 'react';
import {
  SimpleGrid,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Text,
  Badge,
  useColorModeValue,
  Box,
  VStack,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { UMAPPoint } from '../types/latent-space';
import { getClusterColor, getClusterSummary } from '../utils/visualization';

interface ClusterCardsPanelProps {
  points: UMAPPoint[];
  colorPalette: string;
}

export function ClusterCardsPanel({ points, colorPalette }: ClusterCardsPanelProps) {
  const {
    selectedCluster,
    setSelectedCluster,
    clusterLabels,
  } = useLatentSpaceStore();

  // Derive clusters summary
  const clusters = React.useMemo(() => {
    const map: Record<number, number> = {};
    points.forEach((p) => {
      if (p.cluster_id === undefined || p.cluster_id === null || p.cluster_id === -1) return;
      map[p.cluster_id] = (map[p.cluster_id] || 0) + 1;
    });
    return Object.entries(map).map(([id, count]) => ({ id: Number(id), count }));
  }, [points]);

  const bgActive = useColorModeValue('purple.100', 'purple.700');
  const borderDefault = useColorModeValue('gray.200', 'gray.600');

  if (clusters.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Clusters</Heading>
      </CardHeader>
      <CardBody>
        <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
          {clusters.map((c) => {
            const isActive = selectedCluster === c.id;
            const color = getClusterColor({ cluster_id: c.id, is_outlier: false } as any, clusters.length, colorPalette as any);
            const swatch = `rgb(${color[0]},${color[1]},${color[2]})`;
            return (
              <Box
                key={c.id}
                as="button"
                onClick={() => setSelectedCluster(isActive ? null : c.id)}
                border="2px solid"
                borderColor={isActive ? 'purple.500' : borderDefault}
                borderRadius="md"
                p={2}
                bg={isActive ? bgActive : 'transparent'}
                transition="all 0.2s"
              >
                <VStack spacing={1}>
                  <Box w="16px" h="16px" borderRadius="full" bg={swatch} />
                  <Text fontSize="xs">{clusterLabels[c.id] || `#${c.id}`}</Text>
                  <Badge colorScheme="gray" fontSize="0.6rem">{c.count}</Badge>
                  {(()=>{const sum=getClusterSummary(points,c.id);return(
                    <Text fontSize="8px" color="gray.500">D:{sum.density.toFixed(1)} S:{sum.spread.toFixed(1)}</Text>
                  );})()}
                </VStack>
              </Box>
            );
          })}
        </SimpleGrid>
      </CardBody>
    </Card>
  );
} 