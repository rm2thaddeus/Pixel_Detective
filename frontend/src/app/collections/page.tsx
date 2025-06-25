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
import { FiPlus, FiTrash2, FiCheckCircle, FiInfo, FiLayers } from 'react-icons/fi';
import { Header } from '@/components/Header';
import { useState } from 'react';
import { CollectionModal } from '@/components/CollectionModal';
import { CollectionDetailsDrawer } from '@/components/CollectionDetailsDrawer';
import { getCollections, selectCollection, deleteCollection } from '@/lib/api';
import { useStore } from '@/store/useStore';
import { MergeCollectionsModal } from '@/components/MergeCollectionsModal';


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
            isDisabled={isActive}
          />
        </HStack>
      </CardBody>
    </Card>
  );
};


export default function CollectionsPage() {
  const {
    isOpen: isCreateOpen,
    onOpen: openCreate,
    onClose: closeCreate,
  } = useDisclosure();
  const { data: collections, isLoading, error } = useQuery<string[], Error>({
      queryKey: ['collections'],
      queryFn: getCollections
  });
  const activeCollection = useStore((state) => state.collection);
  const setActiveCollection = useStore((state) => state.setCollection);
  const queryClient = useQueryClient();
  const toast = useToast();
  const [detailsCollection, setDetailsCollection] = useState<string | null>(null);
  const {
    isOpen: isDrawerOpen,
    onOpen: openDrawer,
    onClose: closeDrawer,
  } = useDisclosure();
  const {
    isOpen: isMergeOpen,
    onOpen: openMerge,
    onClose: closeMerge,
  } = useDisclosure();

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

  const deleteMutation = useMutation({
    mutationFn: deleteCollection,
    onSuccess: (_, deletedName) => {
      toast({
        title: 'Collection deleted.',
        description: `Collection '${deletedName}' has been removed.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      if (deletedName === activeCollection) {
        setActiveCollection('');
      }
      queryClient.invalidateQueries({ queryKey: ['collections'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error deleting collection.',
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

  const handleDelete = (collectionName: string) => {
    if (window.confirm(`Are you sure you want to delete collection '${collectionName}'? This action cannot be undone.`)) {
      deleteMutation.mutate(collectionName);
    }
  };

  const handleViewDetails = (collectionName: string) => {
    setDetailsCollection(collectionName);
    openDrawer();
  };

  return (
    <Box minH="100vh">
      <Header />
      <Box p={8}>
        <HStack justifyContent="space-between" mb={8}>
          <Heading as="h1" size="xl">
            Collection Management
          </Heading>
          <HStack>
            <Button leftIcon={<FiPlus />} colorScheme="blue" onClick={openCreate}>
              Create Collection
            </Button>
            <Button leftIcon={<FiLayers />} variant="outline" onClick={openMerge}>
              Merge
            </Button>
          </HStack>
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
            {[...collections].sort((a,b)=> (a===activeCollection?-1:b===activeCollection?1:0)).map(name => (
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
        
        <CollectionModal isOpen={isCreateOpen} onClose={closeCreate} />
        <CollectionDetailsDrawer
          isOpen={isDrawerOpen}
          onClose={closeDrawer}
          collectionName={detailsCollection}
        />
        <MergeCollectionsModal isOpen={isMergeOpen} onClose={closeMerge} />
      </Box>
    </Box>
  );
}; 