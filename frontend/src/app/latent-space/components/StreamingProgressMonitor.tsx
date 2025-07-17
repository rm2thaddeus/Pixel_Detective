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
  useColorModeValue
} from '@chakra-ui/react';
import { FiX, FiPlay, FiPause, FiCheck, FiAlertCircle } from 'react-icons/fi';
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

  if (jobs.length === 0) {
    return null;
  }

  const getStatusColor = (status: string) => {
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
      case 'processing': return <Spinner size="sm" />;
      case 'pending': return <FiPlay />;
      case 'failed': return <FiAlertCircle />;
      case 'cancelled': return <FiX />;
      default: return <FiPlay />;
    }
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  const formatEstimatedCompletion = (estimatedCompletion?: number) => {
    if (!estimatedCompletion) return 'Unknown';
    
    const now = Date.now() / 1000;
    const remaining = estimatedCompletion - now;
    
    if (remaining <= 0) return 'Completing...';
    
    return `~${formatTime(remaining)} remaining`;
  };

  return (
    <Box
      position="fixed"
      bottom={4}
      right={4}
      width="400px"
      maxHeight="600px"
      bg={bgColor}
      border="1px solid"
      borderColor={borderColor}
      borderRadius="lg"
      boxShadow="lg"
      zIndex={1000}
      overflow="hidden"
    >
      {/* Header */}
      <Box
        p={3}
        borderBottom="1px solid"
        borderColor={borderColor}
        bg={useColorModeValue('gray.50', 'gray.700')}
      >
        <HStack justify="space-between">
          <Text fontWeight="semibold" color={textColor}>
            Processing Jobs ({jobs.length})
          </Text>
          <Badge colorScheme="blue" variant="subtle">
            {jobs.filter(j => j.status === 'processing' || j.status === 'pending').length} active
          </Badge>
        </HStack>
      </Box>

      {/* Jobs List */}
      <Box maxHeight="500px" overflowY="auto">
        <VStack spacing={0} align="stretch">
          {jobs.map((job) => (
            <Box
              key={job.job_id}
              p={3}
              borderBottom="1px solid"
              borderColor={borderColor}
              _last={{ borderBottom: 'none' }}
              cursor={onExpand ? 'pointer' : 'default'}
              onClick={() => onExpand?.(job.job_id)}
            >
              {/* Job Header */}
              <HStack justify="space-between" mb={2}>
                <HStack spacing={2}>
                  {getStatusIcon(job.status)}
                  <Text fontSize="sm" fontWeight="medium" color={textColor}>
                    Job {job.job_id.slice(0, 8)}
                  </Text>
                  <Badge colorScheme={getStatusColor(job.status)} size="sm">
                    {job.status}
                  </Badge>
                </HStack>
                
                <HStack spacing={1}>
                  {job.status === 'processing' && (
                    <Text fontSize="xs" color="gray.500">
                      {formatEstimatedCompletion(job.estimated_completion)}
                    </Text>
                  )}
                  
                  {job.status !== 'completed' && job.status !== 'failed' && (
                    <IconButton
                      size="xs"
                      icon={<FiX />}
                      aria-label="Cancel job"
                      variant="ghost"
                      colorScheme="red"
                      onClick={(e) => {
                        e.stopPropagation();
                        onCancelJob(job.job_id);
                      }}
                    />
                  )}
                </HStack>
              </HStack>

              {/* Progress Bar */}
              <Progress
                value={job.progress_percentage}
                colorScheme={getStatusColor(job.status)}
                size="sm"
                mb={2}
              />

              {/* Progress Details */}
              <HStack justify="space-between" fontSize="xs" color="gray.500">
                <Text>
                  {job.processed_points.toLocaleString()} / {job.total_points.toLocaleString()} points
                </Text>
                <Text>
                  {job.progress_percentage.toFixed(1)}%
                </Text>
              </HStack>

              {/* Chunk Progress */}
              <Text fontSize="xs" color="gray.500">
                Chunk {job.current_chunk} / {job.total_chunks} • {formatTime(job.processing_time)}
              </Text>

              {/* Error Message */}
              {job.error && (
                <Collapse in={expandedJobs.has(job.job_id)}>
                  <Alert status="error" size="sm" mt={2}>
                    <AlertIcon />
                    <Text fontSize="xs">{job.error}</Text>
                  </Alert>
                </Collapse>
              )}

              {/* Result Summary */}
              {job.status === 'completed' && job.result && (
                <Collapse in={expandedJobs.has(job.job_id)}>
                  <Alert status="success" size="sm" mt={2}>
                    <AlertIcon />
                    <VStack align="start" spacing={1}>
                      <Text fontSize="xs" fontWeight="medium">
                        Processing completed successfully!
                      </Text>
                      <Text fontSize="xs">
                        Time: {formatTime(job.result.processing_time || 0)}
                      </Text>
                      {job.result.chunks_processed && (
                        <Text fontSize="xs">
                          Chunks: {job.result.chunks_processed}
                        </Text>
                      )}
                    </VStack>
                  </Alert>
                </Collapse>
              )}
            </Box>
          ))}
        </VStack>
      </Box>

      {/* Overall Progress */}
      {jobs.length > 1 && (
        <Box
          p={3}
          borderTop="1px solid"
          borderColor={borderColor}
          bg={useColorModeValue('gray.50', 'gray.700')}
        >
          <VStack spacing={2} align="stretch">
            <HStack justify="space-between">
              <Text fontSize="sm" fontWeight="medium" color={textColor}>
                Overall Progress
              </Text>
              <Text fontSize="sm" color="gray.500">
                {jobs.filter(j => j.status === 'completed').length} / {jobs.length} completed
              </Text>
            </HStack>
            
            <Progress
              value={(jobs.filter(j => j.status === 'completed').length / jobs.length) * 100}
              colorScheme="green"
              size="sm"
            />
          </VStack>
        </Box>
      )}
    </Box>
  );
}

// Compact version for smaller screens
export function CompactStreamingProgressMonitor({
  jobs,
  onCancelJob
}: {
  jobs: JobStatus[];
  onCancelJob: (jobId: string) => void;
}) {
  const activeJobs = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
  
  if (activeJobs.length === 0) {
    return null;
  }

  const overallProgress = activeJobs.reduce((sum, job) => sum + job.progress_percentage, 0) / activeJobs.length;

  return (
    <Box
      position="fixed"
      bottom={4}
      right={4}
      width="300px"
      bg="white"
      border="1px solid"
      borderColor="gray.200"
      borderRadius="lg"
      boxShadow="lg"
      p={3}
      zIndex={1000}
    >
      <HStack justify="space-between" mb={2}>
        <Text fontSize="sm" fontWeight="medium">
          Processing ({activeJobs.length})
        </Text>
        <Spinner size="sm" />
      </HStack>
      
      <Progress value={overallProgress} colorScheme="blue" size="sm" mb={2} />
      
      <Text fontSize="xs" color="gray.500">
        {overallProgress.toFixed(1)}% complete
      </Text>
    </Box>
  );
} 