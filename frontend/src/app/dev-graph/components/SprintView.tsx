'use client';

import { Box, VStack, HStack, Text, Select, Badge, useColorModeValue, Divider, Progress } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { FiCalendar, FiGitCommit, FiFile, FiUsers } from 'react-icons/fi';

export interface Sprint {
  number: string;
  start_date: string;
  end_date: string;
  commit_range: {
    start: string;
    end: string;
  };
  metrics: {
    total_commits: number;
    files_changed: number;
    requirements_implemented: number;
    authors: number;
  };
}

export interface SprintViewProps {
  sprints: Sprint[];
  onSprintSelect: (sprint: Sprint) => void;
  selectedSprint?: Sprint;
}

export function SprintView({ sprints, onSprintSelect, selectedSprint }: SprintViewProps) {
  const [filteredSprints, setFilteredSprints] = useState<Sprint[]>([]);
  const [sortBy, setSortBy] = useState<string>('number');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const accentColor = useColorModeValue('green.500', 'green.400');

  useEffect(() => {
    const sorted = [...sprints];
    
    // Sort sprints
    sorted.sort((a, b) => {
      let aVal: number | string;
      let bVal: number | string;
      
      switch (sortBy) {
        case 'number':
          aVal = parseInt(a.number);
          bVal = parseInt(b.number);
          break;
        case 'start_date':
          aVal = new Date(a.start_date).getTime();
          bVal = new Date(b.start_date).getTime();
          break;
        case 'commits':
          aVal = a.metrics.total_commits;
          bVal = b.metrics.total_commits;
          break;
        case 'files':
          aVal = a.metrics.files_changed;
          bVal = b.metrics.files_changed;
          break;
        default:
          aVal = a.number;
          bVal = b.number;
      }
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
    
    setFilteredSprints(sorted);
  }, [sprints, sortBy, sortOrder]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getSprintProgress = (sprint: Sprint) => {
    const now = new Date();
    const start = new Date(sprint.start_date);
    const end = new Date(sprint.end_date);
    
    if (now < start) return 0;
    if (now > end) return 100;
    
    const total = end.getTime() - start.getTime();
    const elapsed = now.getTime() - start.getTime();
    return Math.round((elapsed / total) * 100);
  };

  const getSprintStatus = (sprint: Sprint) => {
    const now = new Date();
    const start = new Date(sprint.start_date);
    const end = new Date(sprint.end_date);
    
    if (now < start) return { status: 'Upcoming', color: 'blue' };
    if (now > end) return { status: 'Completed', color: 'green' };
    return { status: 'Active', color: 'orange' };
  };

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <HStack>
            <FiCalendar />
            <Text fontSize="lg" fontWeight="bold">Sprint Timeline</Text>
          </HStack>
          <Badge colorScheme="green" variant="subtle">
            {sprints.length} Sprints
          </Badge>
        </HStack>

        {/* Controls */}
        <HStack spacing={4}>
          <Box>
            <Text fontSize="sm" mb={1}>Sort By</Text>
            <Select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              size="sm"
            >
              <option value="number">Sprint Number</option>
              <option value="start_date">Start Date</option>
              <option value="commits">Total Commits</option>
              <option value="files">Files Changed</option>
            </Select>
          </Box>
          
          <Box>
            <Text fontSize="sm" mb={1}>Order</Text>
            <Select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
              size="sm"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </Select>
          </Box>
        </HStack>

        <Divider />

        {/* Sprint List */}
        <VStack spacing={3} align="stretch" maxH="600px" overflowY="auto">
          {filteredSprints.map((sprint) => {
            const status = getSprintStatus(sprint);
            const progress = getSprintProgress(sprint);
            const isSelected = selectedSprint?.number === sprint.number;
            
            return (
              <Box
                key={sprint.number}
                p={4}
                borderWidth={1}
                borderColor={isSelected ? accentColor : borderColor}
                borderRadius="md"
                bg={isSelected ? `${accentColor}10` : bgColor}
                cursor="pointer"
                onClick={() => onSprintSelect(sprint)}
                _hover={{
                  borderColor: accentColor,
                  transform: 'translateY(-1px)',
                  boxShadow: 'md',
                }}
                transition="all 0.2s"
              >
                <VStack spacing={3} align="stretch">
                  {/* Sprint Header */}
                  <HStack justify="space-between" align="center">
                    <HStack>
                      <Badge colorScheme={status.color} variant="solid">
                        {status.status}
                      </Badge>
                      <Text fontWeight="bold">Sprint {sprint.number}</Text>
                    </HStack>
                    <Text fontSize="sm" color="gray.500">
                      {formatDate(sprint.start_date)} - {formatDate(sprint.end_date)}
                    </Text>
                  </HStack>

                  {/* Progress Bar */}
                  <Box>
                    <HStack justify="space-between" mb={1}>
                      <Text fontSize="sm">Progress</Text>
                      <Text fontSize="sm" fontWeight="medium">{progress}%</Text>
                    </HStack>
                    <Progress
                      value={progress}
                      colorScheme={status.color}
                      size="sm"
                      borderRadius="full"
                    />
                  </Box>

                  {/* Metrics */}
                  <HStack spacing={6} justify="center">
                    <VStack spacing={1}>
                      <FiGitCommit />
                      <Text fontSize="sm" fontWeight="medium">{sprint.metrics.total_commits}</Text>
                      <Text fontSize="xs" color="gray.500">Commits</Text>
                    </VStack>
                    
                    <VStack spacing={1}>
                      <FiFile />
                      <Text fontSize="sm" fontWeight="medium">{sprint.metrics.files_changed}</Text>
                      <Text fontSize="xs" color="gray.500">Files</Text>
                    </VStack>
                    
                    <VStack spacing={1}>
                      <FiUsers />
                      <Text fontSize="sm" fontWeight="medium">{sprint.metrics.authors}</Text>
                      <Text fontSize="xs" color="gray.500">Authors</Text>
                    </VStack>
                  </HStack>

                  {/* Commit Range */}
                  <Box>
                    <Text fontSize="xs" color="gray.500" mb={1}>Commit Range</Text>
                    <HStack spacing={2} fontSize="xs">
                      <Text fontFamily="mono">{sprint.commit_range.start.substring(0, 8)}</Text>
                      <Text>→</Text>
                      <Text fontFamily="mono">{sprint.commit_range.end.substring(0, 8)}</Text>
                    </HStack>
                  </Box>
                </VStack>
              </Box>
            );
          })}
        </VStack>

        {filteredSprints.length === 0 && (
          <Box textAlign="center" py={8}>
            <Text color="gray.500">No sprints available</Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
