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
  const { clusteringParams, updateClusteringParams } = useLatentSpaceStore();
  const { clusteringMutation } = useUMAP();
  const toast = useToast();

  const debouncedParameterUpdate = useCallback(
    debounce((params: ClusteringRequest) => {
      clusteringMutation.mutate(params, {
        onSuccess: () => {
          toast({
            title: 'Clustering updated',
            status: 'success',
            duration: 2000,
          });
        },
        onError: (error) => {
          toast({
            title: 'Clustering failed',
            description: error.message,
            status: 'error',
            duration: 4000,
          });
        },
      });
    }, 1000),
    [clusteringMutation, toast]
  );

  const handleParameterChange = (newParams: Partial<ClusteringRequest>) => {
    const updatedParams = { ...clusteringParams, ...newParams };
    updateClusteringParams(newParams);
    onParametersChange?.(updatedParams);
    debouncedParameterUpdate(updatedParams);
  };

  const renderAlgorithmSpecificControls = () => {
    switch (clusteringParams.algorithm) {
      case 'dbscan':
        return (
          <>
            <FormControl>
              <FormLabel>Eps (neighborhood distance)</FormLabel>
              <NumberInput
                value={clusteringParams.eps}
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
                value={clusteringParams.min_samples}
                min={1}
                max={20}
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
              value={clusteringParams.n_clusters || 5}
              min={2}
              max={20}
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
