'use client';

import React, { useState, useCallback } from 'react';
import {
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Button,
  Text,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Divider,
  useToast,
} from '@chakra-ui/react';
import { ClusteringRequest } from '../types/latent-space';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { useUMAP } from '../hooks/useUMAP';
import { debounce } from 'lodash';

interface ClusteringControlsProps {
  onParametersChange?: (params: ClusteringRequest) => void;
}

export function ClusteringControls({ onParametersChange }: ClusteringControlsProps) {
  const { 
    clusteringParams, 
    updateClusteringParams, 
    setProjectionData, 
    projectionData 
  } = useLatentSpaceStore();
  const { clusteringMutation } = useUMAP();
  const toast = useToast();

  const debouncedParameterUpdate = useCallback(
    debounce((params: ClusteringRequest) => {
      if (!projectionData?.points || projectionData.points.length === 0) {
        toast({
          title: 'No data available',
          description: 'Cannot apply clustering without projection data.',
          status: 'warning',
          duration: 3000,
        });
        return;
      }

      console.log('🔄 Applying clustering with params:', params);
      clusteringMutation.mutate({ ...params, points: projectionData.points }, {
        onSuccess: (data) => {
          console.log('✅ Clustering update successful:', data);
          setProjectionData(data);
          toast({
            title: 'Clustering updated',
            status: 'success',
            duration: 2000,
          });
        },
        onError: (error) => {
          console.error('❌ Clustering update failed:', error);
          toast({
            title: 'Clustering failed',
            description: error.message,
            status: 'error',
            duration: 4000,
          });
        },
      });
    }, 1000),
    [clusteringMutation, toast, setProjectionData, projectionData]
  );

  const handleParameterChange = (newParams: Partial<ClusteringRequest>) => {
    const updatedParams = { ...clusteringParams, ...newParams };
    updateClusteringParams(newParams);
    onParametersChange?.(updatedParams);
    
    // Only auto-update if we have significant parameter changes
    const shouldAutoUpdate = 
      newParams.algorithm ||
      (newParams.n_clusters && Math.abs((newParams.n_clusters || 0) - (clusteringParams.n_clusters || 0)) > 0) ||
      (newParams.eps && Math.abs(newParams.eps - clusteringParams.eps) > 0.05) ||
      (newParams.min_samples && newParams.min_samples !== clusteringParams.min_samples);
    
    if (shouldAutoUpdate) {
      debouncedParameterUpdate({ ...clusteringParams, ...newParams });
    }
  };

  const renderAlgorithmSpecificControls = () => {
    switch (clusteringParams.algorithm) {
      case 'dbscan':
        return (
          <>
            <FormControl>
              <FormLabel>Eps (neighborhood distance)</FormLabel>
              <NumberInput
                value={clusteringParams.eps ?? 0.5}
                min={0.1}
                max={2.0}
                step={0.1}
                onChange={(_, value) => handleParameterChange({ eps: value })}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel>Min Samples</FormLabel>
              <NumberInput
                value={clusteringParams.min_samples ?? 5}
                min={1}
                max={50}
                onChange={(_, value) => handleParameterChange({ min_samples: value })}
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
          </>
        );
      case 'kmeans':
      case 'hierarchical':
        return (
          <FormControl>
            <FormLabel>Number of Clusters</FormLabel>
            <NumberInput
              value={clusteringParams.n_clusters ?? 5}
              min={2}
              max={50}
              onChange={(_, value) => handleParameterChange({ n_clusters: value })}
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        );
      default:
        return null;
    }
  };

  return (
    <Card>
      <CardHeader>
        <Heading size="md">Clustering Controls</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          <FormControl>
            <FormLabel>Algorithm</FormLabel>
            <Select
              value={clusteringParams.algorithm}
              onChange={(e) =>
                handleParameterChange({ 
                  algorithm: e.target.value as ClusteringRequest['algorithm'] 
                })
              }
            >
              <option value="dbscan">DBSCAN</option>
              <option value="kmeans">K-Means</option>
              <option value="hierarchical">Hierarchical</option>
            </Select>
          </FormControl>

          <Divider />

          {renderAlgorithmSpecificControls()}

          <Button
            isLoading={clusteringMutation.isPending}
            loadingText="Updating..."
            onClick={() => debouncedParameterUpdate(clusteringParams)}
            colorScheme="blue"
          >
            Apply Clustering
          </Button>
        </VStack>
      </CardBody>
    </Card>
  );
}
