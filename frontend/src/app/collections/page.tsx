'use client';

import {
  Box,
  Heading,
  Text,
  Button,
  VStack,
  HStack,
  useToast,
  SimpleGrid,
  Spinner,
  Alert,
  AlertIcon,
  Card,
  CardHeader,
  CardBody,
  Tag,
  IconButton,
  Flex,
  Spacer,
  useDisclosure,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FiPlus, FiTrash2, FiCheckCircle, FiInfo } from 'react-icons/fi';
import { useState } from 'react';
import { CollectionModal } from '@/components/CollectionModal';
import { getCollections, selectCollection, CollectionInfo, getCollectionInfo } from '@/lib/api';
import { useStore } from '@/store/useStore';


const CollectionCard = ({ name, isActive, onSelect, onDelete, onView }) => {
  return (
    <Card>
      <CardHeader>
        <Flex>
          <Heading size='md'>{name}</Heading>
          <Spacer />
          {isActive && <Tag colorScheme="green">Active</Tag>}
        </Flex>
      </CardHeader>
      <CardBody>
        <Text>Manage images and settings for this collection.</Text>
        <HStack mt={4} spacing={2}>
          <Button 
            size="sm" 
            leftIcon={<FiCheckCircle />} 
            onClick={() => onSelect(name)}
            isDisabled={isActive}
            colorScheme={isActive ? 'green' : 'gray'}
          >
            {isActive ? 'Selected' : 'Select'}
          </Button>
          <Button size="sm" leftIcon={<FiInfo />} onClick={() => onView(name)}>
            Details
          </Button>
          <Spacer />
          <IconButton
            aria-label="Delete collection"
            icon={<FiTrash2 />}
            size="sm"
            variant="ghost"
            colorScheme="red"
            onClick={() => onDelete(name)}
          />
        </HStack>
      </CardBody>
    </Card>
  );
};


export default function CollectionsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { data: collections, isLoading, error } = useQuery<string[], Error>({
      queryKey: ['collections'],
      queryFn: getCollections
  });
  const activeCollection = useStore((state) => state.collection);
  const setActiveCollection = useStore((state) => state.setCollection);
  const queryClient = useQueryClient();
  const toast = useToast();

  const selectionMutation = useMutation({
    mutationFn: selectCollection,
    onSuccess: (data, variables) => {
      setActiveCollection(variables);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['collectionInfo', activeCollection] });
      queryClient.invalidateQueries({ queryKey: ['collectionInfo', variables] });
      toast({
        title: 'Collection selected.',
        description: `'${variables}' is now the active collection.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error selecting collection.',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const handleSelect = (collectionName: string) => {
    selectionMutation.mutate(collectionName);
  };

  // Placeholder functions for delete and view details
  const handleDelete = (collectionName: string) => {
    toast({
        title: `Delete clicked for ${collectionName}`,
        status: 'info',
        duration: 2000,
    });
  };

  const handleViewDetails = (collectionName: string) => {
      toast({
        title: `View details for ${collectionName}`,
        status: 'info',
        duration: 2000,
    });
  };

  return (
    <Box p={8}>
      <HStack justifyContent="space-between" mb={8}>
        <Heading as="h1" size="xl">
          Collection Management
        </Heading>
        <Button leftIcon={<FiPlus />} colorScheme="blue" onClick={onOpen}>
          Create Collection
        </Button>
      </HStack>
      <Text mb={8} fontSize="lg" color="gray.600">
        Here you can create, view, and manage all your image collections. Select a collection to make it active for searching and ingestion.
      </Text>

      {isLoading && (
        <VStack>
          <Spinner />
          <Text>Loading collections...</Text>
        </VStack>
      )}

      {error && (
        <Alert status="error">
          <AlertIcon />
          {`There was an error loading your collections: ${error.message}`}
        </Alert>
      )}

      {collections && (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
          {collections.map(name => (
            <CollectionCard
              key={name}
              name={name}
              isActive={name === activeCollection}
              onSelect={handleSelect}
              onDelete={handleDelete}
              onView={handleViewDetails}
            />
          ))}
        </SimpleGrid>
      )}
      
      <CollectionModal isOpen={isOpen} onClose={onClose} />
    </Box>
  );
}; 