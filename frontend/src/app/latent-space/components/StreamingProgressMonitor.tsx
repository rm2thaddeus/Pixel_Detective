'use client';

import React from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  IconButton,
  Collapse,
  Alert,
  AlertIcon,
  Spinner,
  useColorModeValue,
  Button,
  Divider,
  Flex,
  Tooltip
} from '@chakra-ui/react';
import { FiX, FiPlay, FiPause, FiCheck, FiAlertCircle, FiClock, FiZap } from 'react-icons/fi';
import { JobStatus } from '../hooks/useStreamingUMAP';

interface StreamingProgressMonitorProps {
  jobs: JobStatus[];
  onCancelJob: (jobId: string) => void;
  onExpand?: (jobId: string) => void;
  expandedJobs?: Set<string>;
}

export function StreamingProgressMonitor({ 
  jobs, 
  onCancelJob, 
  onExpand,
  expandedJobs = new Set()
}: StreamingProgressMonitorProps) {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.300');

  if (jobs.length === 0) return null;

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const formatEstimatedCompletion = (timestamp?: number): string => {
    if (!timestamp) return 'Calculating...';
    const now = Date.now() / 1000;
    const remaining = timestamp - now;
    if (remaining <= 0) return 'Completing...';
    return `~${formatTime(remaining)} remaining`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed': return 'green';
      case 'processing': return 'blue';
      case 'pending': return 'yellow';
      case 'failed': return 'red';
      case 'cancelled': return 'gray';
      default: return 'gray';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <FiCheck />;
      case 'processing': return <FiZap />;
      case 'pending': return <FiClock />;
      case 'failed': return <FiAlertCircle />;
      case 'cancelled': return <FiX />;
      default: return <FiClock />;
    }
  };

  const getJobType = (jobId: string): string => {
    // This is a simple heuristic - in a real app you might store job type in the job object
    return jobId.includes('umap') ? 'UMAP' : 'Clustering';
  };

  return (
    <Box
      position="fixed"
      bottom={4}
      right={4}
      width="400px"
      maxHeight="80vh"
      overflowY="auto"
      zIndex={1000}
    >
      <VStack spacing={3} align="stretch">
        {jobs.map((job) => (
          <Box
            key={job.job_id}
            bg={bgColor}
            border="1px solid"
            borderColor={borderColor}
            borderRadius="lg"
            p={4}
            shadow="lg"
            position="relative"
          >
            {/* Job Header */}
            <Flex justify="space-between" align="center" mb={3}>
              <HStack spacing={2}>
                <Badge colorScheme={getStatusColor(job.status)} variant="subtle">
                  {getJobType(job.job_id)}
                </Badge>
                <Text fontSize="sm" fontWeight="medium" color={textColor}>
                  {job.job_id.slice(0, 8)}...
                </Text>
              </HStack>
              
              <HStack spacing={2}>
                <Tooltip label={formatEstimatedCompletion(job.estimated_completion)}>
                  <Box>
                    {getStatusIcon(job.status)}
                  </Box>
                </Tooltip>
                
                {job.status === 'processing' && (
                  <IconButton
                    size="sm"
                    variant="ghost"
                    icon={<FiX />}
                    aria-label="Cancel job"
                    onClick={() => onCancelJob(job.job_id)}
                    colorScheme="red"
                  />
                )}
              </HStack>
            </Flex>

            {/* Progress Bar */}
            {job.status === 'processing' && (
              <VStack spacing={2} align="stretch" mb={3}>
                <Progress 
                  value={job.progress_percentage} 
                  colorScheme="blue" 
                  size="sm"
                  borderRadius="full"
                />
                <HStack justify="space-between" fontSize="xs" color={mutedTextColor}>
                  <Text>{job.progress_percentage.toFixed(1)}% complete</Text>
                  <Text>{formatTime(job.processing_time)} elapsed</Text>
                </HStack>
              </VStack>
            )}

            {/* Job Details */}
            <VStack spacing={1} align="stretch" fontSize="sm">
              <HStack justify="space-between">
                <Text color={mutedTextColor}>Status:</Text>
                <Badge colorScheme={getStatusColor(job.status)} size="sm">
                  {job.status}
                </Badge>
              </HStack>
              
              <HStack justify="space-between">
                <Text color={mutedTextColor}>Points:</Text>
                <Text color={textColor}>
                  {job.processed_points.toLocaleString()} / {job.total_points.toLocaleString()}
                </Text>
              </HStack>
              
              {job.total_chunks > 1 && (
                <HStack justify="space-between">
                  <Text color={mutedTextColor}>Chunks:</Text>
                  <Text color={textColor}>
                    {job.current_chunk} / {job.total_chunks}
                  </Text>
                </HStack>
              )}
            </VStack>

            {/* Error Display */}
            {job.status === 'failed' && job.error && (
              <Alert status="error" size="sm" mt={3}>
                <AlertIcon />
                <Text fontSize="xs">{job.error}</Text>
              </Alert>
            )}

            {/* Success Message */}
            {job.status === 'completed' && (
              <Alert status="success" size="sm" mt={3}>
                <AlertIcon />
                <Text fontSize="xs">
                  Completed in {formatTime(job.processing_time)}
                </Text>
              </Alert>
            )}

            {/* Expandable Details */}
            {job.result && (
              <Collapse in={expandedJobs.has(job.job_id)}>
                <Divider my={3} />
                <VStack spacing={2} align="stretch" fontSize="xs">
                  <Text fontWeight="medium" color={textColor}>Results:</Text>
                  <Text color={mutedTextColor}>
                    {job.result.embeddings ? 
                      `${job.result.embeddings.length} embeddings generated` :
                      `${job.result.labels?.length || 0} labels assigned`
                    }
                  </Text>
                  {job.result.silhouette_score && (
                    <Text color={mutedTextColor}>
                      Silhouette score: {job.result.silhouette_score.toFixed(3)}
                    </Text>
                  )}
                  {job.result.clusters && (
                    <Text color={mutedTextColor}>
                      {Object.keys(job.result.clusters).length} clusters found
                    </Text>
                  )}
                </VStack>
              </Collapse>
            )}

            {/* Expand/Collapse Button */}
            {job.result && (
              <Button
                size="xs"
                variant="ghost"
                onClick={() => onExpand?.(job.job_id)}
                mt={2}
                width="100%"
              >
                {expandedJobs.has(job.job_id) ? 'Hide Details' : 'Show Details'}
              </Button>
            )}
          </Box>
        ))}
      </VStack>
    </Box>
  );
} 