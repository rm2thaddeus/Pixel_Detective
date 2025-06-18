'use client';

import React, { useState } from 'react';
import {
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  useToast,
  Box,
  Badge,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { useUMAP } from '../hooks/useUMAP';
import { ClusterLabelRequest } from '../types/latent-space';

export function ClusterLabelingPanel() {
  const { projectionData, setClusterLabel, clusterLabels } = useLatentSpaceStore();
  const { labelMutation } = useUMAP();
  const toast = useToast();
  const [localLabels, setLocalLabels] = useState<Record<number, string>>({});

  const handleLabelChange = (clusterId: number, label: string) => {
    setLocalLabels(prev => ({ ...prev, [clusterId]: label }));
  };

  const handleSaveLabel = (clusterId: number) => {
    const label = localLabels[clusterId];
    if (!label) return;

    const request: ClusterLabelRequest = { cluster_id: clusterId, label };
    labelMutation.mutate(request, {
      onSuccess: () => {
        setClusterLabel(clusterId, label); // Update global store
        toast({
          title: `Cluster ${clusterId} labeled as "${label}"`,
          status: 'success',
          duration: 2000,
        });
      },
      onError: (error) => {
        toast({
          title: 'Failed to save label',
          description: error.message,
          status: 'error',
        });
      },
    });
  };

  if (!projectionData?.clustering_info?.n_clusters) {
    return null;
  }
  
  const clusterIds = [...new Set(projectionData.points.map(p => p.cluster_id).filter(id => id !== undefined && id !== null))]
    .sort((a, b) => a - b);

  return (
    <Card>
      <CardHeader><Heading size="md">Auto-Catalog Clusters</Heading></CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          {clusterIds.map(id => (
            <HStack key={id} spacing={3}>
              <Badge colorScheme="purple" p={2} borderRadius="md">Cluster {id}</Badge>
              <Input
                placeholder={`Name for Cluster ${id}`}
                value={localLabels[id] || clusterLabels[id] || ''}
                onChange={(e) => handleLabelChange(id, e.target.value)}
              />
              <Button
                size="sm"
                onClick={() => handleSaveLabel(id)}
                isLoading={labelMutation.isPending && labelMutation.variables?.cluster_id === id}
              >
                Save
              </Button>
            </HStack>
          ))}
        </VStack>
      </CardBody>
    </Card>
  );
} 