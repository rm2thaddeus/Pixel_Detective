'use client';

import { Box, VStack, HStack, Text, Select, Badge, useColorModeValue, Divider, Progress, SimpleGrid, Button, Icon, UnorderedList, ListItem } from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { FiCalendar, FiGitCommit, FiFile, FiUsers } from 'react-icons/fi';
import { useSprintSubgraph } from '../hooks/useWindowedSubgraph';

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
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
      }
    });
    
    setFilteredSprints(sorted);
  }, [sprints, sortBy, sortOrder]);

  const handleSortChange = (value: string) => {
    setSortBy(value);
  };

  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
  };

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

  if (sprints.length === 0) {
    return (
      <Box p={6} textAlign="center" bg={bgColor} borderRadius="lg" borderWidth="1px" borderColor={borderColor}>
        <Text color="gray.500">No sprints found</Text>
      </Box>
    );
  }

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
      <VStack spacing={4} align="stretch">
        {/* Minimalistic Header */}
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="bold">Sprint View</Text>
          <HStack spacing={2}>
            <Select
              value={sortBy}
              onChange={(e) => handleSortChange(e.target.value)}
              size="sm"
              w="120px"
            >
              <option value="number">Number</option>
              <option value="start_date">Date</option>
              <option value="commits">Commits</option>
              <option value="files">Files</option>
            </Select>
            <Button
              size="sm"
              variant="ghost"
              onClick={toggleSortOrder}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </Button>
          </HStack>
        </HStack>

        {/* Compact Sprint List */}
        <VStack spacing={2} align="stretch" maxH="400px" overflowY="auto">
          {filteredSprints.map((sprint) => {
            const status = getSprintStatus(sprint);
            const progress = getSprintProgress(sprint);
            const isSelected = selectedSprint?.number === sprint.number;
            
            return (
              <Box
                key={sprint.number}
                p={3}
                borderWidth={1}
                borderColor={isSelected ? accentColor : borderColor}
                borderRadius="md"
                bg={isSelected ? `${accentColor}10` : bgColor}
                cursor="pointer"
                onClick={() => onSprintSelect(sprint)}
                _hover={{
                  borderColor: accentColor,
                  bg: `${accentColor}05`,
                }}
                transition="all 0.2s"
              >
                <HStack justify="space-between" align="center">
                  <HStack spacing={3}>
                    <Badge colorScheme={status.color} variant="subtle" size="sm">
                      {status.status}
                    </Badge>
                    <Text fontWeight="medium">Sprint {sprint.number}</Text>
                    <Text fontSize="sm" color="gray.500">
                      {formatDate(sprint.start_date)} - {formatDate(sprint.end_date)}
                    </Text>
                  </HStack>
                  
                  <HStack spacing={4} fontSize="sm" color="gray.600">
                    <HStack spacing={1}>
                      <Icon as={FiGitCommit} boxSize={3} />
                      <Text>{sprint.metrics.total_commits}</Text>
                    </HStack>
                    <HStack spacing={1}>
                      <Icon as={FiFile} boxSize={3} />
                      <Text>{sprint.metrics.files_changed}</Text>
                    </HStack>
                    <HStack spacing={1}>
                      <Icon as={FiUsers} boxSize={3} />
                      <Text>{sprint.metrics.authors}</Text>
                    </HStack>
                    <Text fontSize="xs" color="gray.500">{progress}%</Text>
                  </HStack>
                </HStack>
                
                {/* Compact Progress Bar */}
                <Box mt={2}>
                  <Progress
                    value={progress}
                    colorScheme={status.color}
                    size="xs"
                    borderRadius="full"
                  />
                </Box>
              </Box>
            );
          })}
        </VStack>

        {filteredSprints.length === 0 && (
          <Box textAlign="center" py={8}>
            <Text color="gray.500">No sprints available</Text>
          </Box>
        )}

        {/* Hierarchical Subgraph for selected sprint */}
        {selectedSprint && (
          <Box mt={4} p={3} borderWidth={1} borderColor={borderColor} borderRadius="md" bg={`${accentColor}05`}>
            <Text fontSize="sm" fontWeight="bold" mb={2} color={accentColor}>
              Sprint {selectedSprint.number} Hierarchy
            </Text>
            <SprintHierarchy sprintNumber={selectedSprint.number} />
          </Box>
        )}
      </VStack>
    </Box>
  );
}

export default SprintView;

function SprintHierarchy({ sprintNumber }: { sprintNumber: string }) {
  const { data, isLoading, error } = useSprintSubgraph(sprintNumber);
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const bg = useColorModeValue('gray.50', 'gray.700');

  if (isLoading) return <Text fontSize="sm" color="gray.500">Loading hierarchy…</Text>;
  if (error) return <Text fontSize="sm" color="red.500">Failed to load sprint hierarchy</Text>;

  const nodes = (data?.nodes || []) as any[];
  const edges = (data?.edges || []) as any[];
  const byId = new Map(nodes.map(n => [n.id, n]));
  const containsDoc = edges.filter(e => e.type === 'CONTAINS_DOC');
  const containsChunk = edges.filter(e => e.type === 'CONTAINS_CHUNK');
  const mentions = edges.filter(e => e.type === 'MENTIONS');

  const docIds = containsDoc.map(e => e.to);
  const docs = docIds.map(id => byId.get(id)).filter(Boolean);

  return (
    <Box bg={bg} p={3} borderRadius="md" borderWidth={1} borderColor={borderColor}>
      {docs.length === 0 && <Text fontSize="sm" color="gray.500">No documents linked to this sprint.</Text>}
      <UnorderedList>
        {docs.map((doc: any) => {
          const chunks = containsChunk.filter(e => e.from === (doc.id || doc.path)).map(e => byId.get(e.to)).filter(Boolean);
          return (
            <ListItem key={doc.id || doc.path}>
              <Text fontWeight="medium">{doc.name || doc.path}</Text>
              {chunks.length > 0 && (
                <UnorderedList styleType="circle" ml={5}>
                  {chunks.map((ch: any) => {
                    const reqs = mentions.filter(e => e.from === ch.id).map(e => byId.get(e.to)).filter(Boolean);
                    return (
                      <ListItem key={ch.id}>
                        <Text>{ch.heading || ch.id}</Text>
                        {reqs.length > 0 && (
                          <UnorderedList styleType="square" ml={5}>
                            {reqs.map((r: any) => (
                              <ListItem key={r.id}>
                                <Text fontFamily="mono" fontSize="sm">{r.id}</Text>
                              </ListItem>
                            ))}
                          </UnorderedList>
                        )}
                      </ListItem>
                    );
                  })}
                </UnorderedList>
              )}
            </ListItem>
          );
        })}
      </UnorderedList>
    </Box>
  );
}
