'use client';

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  HStack,
  Input,
  Text,
  Box,
  useToast,
  Spinner,
  Badge
} from '@chakra-ui/react';
import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

interface CollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CollectionModal({ isOpen, onClose }: CollectionModalProps) {
  const { collection, setCollection } = useStore();
  const [collections, setCollections] = useState<string[]>([]);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const toast = useToast();

  const fetchCollections = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get<string[]>('/api/v1/collections');
      setCollections(response.data);
    } catch {
      toast({
        title: 'Error fetching collections',
        description: 'Could not load collections from the server',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const createCollection = async () => {
    if (!newCollectionName.trim()) {
      toast({
        title: 'Invalid name',
        description: 'Please enter a collection name',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setCreating(true);
      await api.post('/api/v1/collections', {
        collection_name: newCollectionName.trim()
      });
      
      toast({
        title: 'Collection created',
        description: `Collection "${newCollectionName}" created successfully`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      setNewCollectionName('');
      await fetchCollections();
    } catch {
      toast({
        title: 'Error creating collection',
        description: 'Could not create the collection',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setCreating(false);
    }
  };

  const selectCollection = async (collectionName: string) => {
    try {
      await api.post('/api/v1/collections/select', {
        collection_name: collectionName
      });
      
      setCollection(collectionName);
      toast({
        title: 'Collection selected',
        description: `Now using collection "${collectionName}"`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      onClose();
    } catch {
      toast({
        title: 'Error selecting collection',
        description: 'Could not select the collection',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchCollections();
    }
  }, [isOpen, fetchCollections]);

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Manage Collections</ModalHeader>
        <ModalCloseButton />
        
        <ModalBody>
          <VStack spacing={4} align="stretch">
            {/* Create new collection */}
            <Box>
              <Text fontWeight="semibold" mb={2}>Create New Collection</Text>
              <HStack>
                <Input
                  placeholder="Enter collection name"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && createCollection()}
                />
                <Button
                  colorScheme="blue"
                  onClick={createCollection}
                  isLoading={creating}
                  loadingText="Creating"
                >
                  Create
                </Button>
              </HStack>
            </Box>

            {/* List existing collections */}
            <Box>
              <Text fontWeight="semibold" mb={2}>Existing Collections</Text>
              {loading ? (
                <Box textAlign="center" py={4}>
                  <Spinner />
                </Box>
              ) : collections.length === 0 ? (
                <Text color="gray.500" textAlign="center" py={4}>
                  No collections found. Create one above.
                </Text>
              ) : (
                <VStack spacing={2} align="stretch">
                  {collections.map((col) => (
                    <HStack
                      key={col}
                      p={3}
                      border="1px"
                      borderColor="gray.200"
                      borderRadius="md"
                      justify="space-between"
                      bg={collection === col ? 'blue.50' : 'white'}
                    >
                      <HStack>
                        <Text>{col}</Text>
                        {collection === col && (
                          <Badge colorScheme="blue" size="sm">Active</Badge>
                        )}
                      </HStack>
                      <Button
                        size="sm"
                        colorScheme="blue"
                        variant={collection === col ? 'solid' : 'outline'}
                        onClick={() => selectCollection(col)}
                        isDisabled={collection === col}
                      >
                        {collection === col ? 'Selected' : 'Select'}
                      </Button>
                    </HStack>
                  ))}
                </VStack>
              )}
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 