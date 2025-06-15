'use client';

import {
  Box,
  VStack,
  HStack,
  Heading,
  Button,
  Divider,
  useColorModeValue,
  Text,
  Badge,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2, FiRefreshCw } from 'react-icons/fi';
import { useStore } from '@/store/useStore';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface SidebarProps {
  onOpenCollectionModal: () => void;
}

const fetchCollections = async () => {
  const { data } = await api.get<string[]>('/api/v1/collections');
  return data;
};

export function Sidebar({ onOpenCollectionModal }: SidebarProps) {
  const { collection, setCollection } = useStore();
  const { data: collections, isLoading, refetch } = useQuery({
    queryKey: ['collections'],
    queryFn: fetchCollections,
  });

  const sidebarBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  return (
    <Box
      as="aside"
      w="280px"
      bg={sidebarBg}
      borderRight="1px"
      borderColor={borderColor}
      p={4}
      h="calc(100vh - 64px)" // Full height minus header
      position="sticky"
      top="64px" // Align below header
    >
      <VStack align="stretch" spacing={4}>
        <HStack justify="space-between">
          <Heading size="md">Collections</Heading>
          <Tooltip label="Refresh Collections" placement="top">
            <IconButton
              aria-label="Refresh Collections"
              icon={<FiRefreshCw />}
              size="sm"
              variant="ghost"
              onClick={() => refetch()}
              isLoading={isLoading}
            />
          </Tooltip>
        </HStack>
        <Button
          leftIcon={<FiPlus />}
          colorScheme="blue"
          onClick={onOpenCollectionModal}
        >
          New Collection
        </Button>
        <Divider />
        <VStack align="stretch" spacing={2}>
          {isLoading && <Text>Loading...</Text>}
          {collections?.map((c) => (
            <Button
              key={c}
              variant={collection === c ? 'solid' : 'ghost'}
              colorScheme={collection === c ? 'blue' : 'gray'}
              onClick={() => setCollection(c)}
              justifyContent="space-between"
            >
              <Text isTruncated>{c}</Text>
              {collection === c && <Badge colorScheme="green">Active</Badge>}
            </Button>
          ))}
        </VStack>
      </VStack>
    </Box>
  );
} 