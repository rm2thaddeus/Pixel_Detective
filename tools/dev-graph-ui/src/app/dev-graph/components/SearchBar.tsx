'use client';

import { HStack, Input, Button, Select, VStack, Text, useColorModeValue, Box, Badge, Collapse, IconButton } from '@chakra-ui/react';
import { useState } from 'react';
import { FiSearch, FiFilter, FiX } from 'react-icons/fi';

export interface SearchFilters {
  nodeType?: string;
  relationshipType?: string;
  timeRange?: {
    start?: string;
    end?: string;
  };
  author?: string;
  commitHash?: string;
}

export function SearchBar({ onSearch }: { onSearch: (q: string, filters: SearchFilters) => void }) {
  const [q, setQ] = useState('');
  const [nodeType, setNodeType] = useState<string>('all');
  const [relationshipType, setRelationshipType] = useState<string>('all');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [author, setAuthor] = useState('');
  const [commitHash, setCommitHash] = useState('');
  const [activeFilters, setActiveFilters] = useState<string[]>([]);
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const handleSearch = () => {
    if (q.trim()) {
      const filters: SearchFilters = {};
      
      if (nodeType !== 'all') filters.nodeType = nodeType;
      if (relationshipType !== 'all') filters.relationshipType = relationshipType;
      if (author.trim()) filters.author = author.trim();
      if (commitHash.trim()) filters.commitHash = commitHash.trim();
      
      // Update active filters display
      const newActiveFilters = [];
      if (filters.nodeType) newActiveFilters.push(`Node: ${filters.nodeType}`);
      if (filters.relationshipType) newActiveFilters.push(`Rel: ${filters.relationshipType}`);
      if (filters.author) newActiveFilters.push(`Author: ${filters.author}`);
      if (filters.commitHash) newActiveFilters.push(`Commit: ${filters.commitHash}`);
      setActiveFilters(newActiveFilters);
      
      onSearch(q.trim(), filters);
    }
  };

  const clearFilters = () => {
    setNodeType('all');
    setRelationshipType('all');
    setAuthor('');
    setCommitHash('');
    setActiveFilters([]);
  };

  const removeFilter = (filterToRemove: string) => {
    const newFilters = activeFilters.filter(f => f !== filterToRemove);
    setActiveFilters(newFilters);
    
    // Update individual filter states
    if (filterToRemove.startsWith('Node:')) setNodeType('all');
    if (filterToRemove.startsWith('Rel:')) setRelationshipType('all');
    if (filterToRemove.startsWith('Author:')) setAuthor('');
    if (filterToRemove.startsWith('Commit:')) setCommitHash('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
      <VStack spacing={4} align="stretch">
        {/* Main Search */}
        <HStack>
          <Input
            placeholder="Search nodes, requirements, files..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyPress={handleKeyPress}
            flex={1}
          />
          <Button
            leftIcon={<FiSearch />}
            onClick={handleSearch}
            colorScheme="green"
            isDisabled={!q.trim()}
          >
            Search
          </Button>
          <IconButton
            aria-label="Toggle advanced filters"
            icon={<FiFilter />}
            onClick={() => setShowAdvanced(!showAdvanced)}
            variant={showAdvanced ? "solid" : "outline"}
            colorScheme="blue"
          />
        </HStack>

        {/* Active Filters Display */}
        {activeFilters.length > 0 && (
          <HStack flexWrap="wrap" spacing={2}>
            <Text fontSize="sm" fontWeight="medium">Active Filters:</Text>
            {activeFilters.map((filter, index) => (
              <Badge
                key={index}
                colorScheme="blue"
                variant="subtle"
                display="flex"
                alignItems="center"
                gap={1}
              >
                {filter}
                <IconButton
                  aria-label="Remove filter"
                  icon={<FiX />}
                  size="xs"
                  variant="ghost"
                  onClick={() => removeFilter(filter)}
                />
              </Badge>
            ))}
            <Button size="xs" variant="ghost" onClick={clearFilters}>
              Clear All
            </Button>
          </HStack>
        )}

        {/* Advanced Filters */}
        <Collapse in={showAdvanced}>
          <VStack spacing={3} align="stretch" pt={2}>
            <HStack spacing={4}>
              <Box flex={1}>
                <Text fontSize="sm" mb={1}>Node Type</Text>
                <Select
                  value={nodeType}
                  onChange={(e) => setNodeType(e.target.value)}
                  size="sm"
                >
                  <option value="all">All Types</option>
                  <option value="Requirement">Requirements</option>
                  <option value="File">Files</option>
                  <option value="Sprint">Sprints</option>
                  <option value="Goal">Goals</option>
                  <option value="GitCommit">Commits</option>
                </Select>
              </Box>
              
              <Box flex={1}>
                <Text fontSize="sm" mb={1}>Relationship Type</Text>
                <Select
                  value={relationshipType}
                  onChange={(e) => setRelationshipType(e.target.value)}
                  size="sm"
                >
                  <option value="all">All Relationships</option>
                  <option value="IMPLEMENTS">Implements</option>
                  <option value="EVOLVES_FROM">Evolves From</option>
                  <option value="DEPENDS_ON">Depends On</option>
                  <option value="REFERENCES">References</option>
                  <option value="PART_OF">Part Of</option>
                  <option value="TOUCHED">Touched</option>
                  <option value="REFACTORED_TO">Refactored To</option>
                </Select>
              </Box>
            </HStack>

            <HStack spacing={4}>
              <Box flex={1}>
                <Text fontSize="sm" mb={1}>Author</Text>
                <Input
                  placeholder="Filter by author email"
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  size="sm"
                />
              </Box>
              
              <Box flex={1}>
                <Text fontSize="sm" mb={1}>Commit Hash</Text>
                <Input
                  placeholder="Filter by commit hash"
                  value={commitHash}
                  onChange={(e) => setCommitHash(e.target.value)}
                  size="sm"
                />
              </Box>
            </HStack>
          </VStack>
        </Collapse>
      </VStack>
    </Box>
  );
}

export default SearchBar;


