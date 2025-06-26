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
  Badge,
  useColorModeValue,
  IconButton,
  Tooltip,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay
} from '@chakra-ui/react';
import { useState, useEffect, useCallback } from 'react';
import { useStore } from '@/store/useStore';
import { api, deleteCollection as deleteCollectionApi } from '@/lib/api';
import { FiTrash2 } from 'react-icons/fi';
import { useMutation, useQueryClient } from '@tanstack/react-query';

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
  const [collectionToDelete, setCollectionToDelete] = useState<string | null>(null);
  const toast = useToast();

  const { isOpen: isAlertOpen, onOpen: onAlertOpen, onClose: onAlertClose } = useDisclosure();
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: (name: string) => deleteCollectionApi(name),
    onSuccess: (_, deletedName) => {
      toast({
        title: 'Collection deleted',
        description: `Collection "${deletedName}" has been deleted`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      if (collection === deletedName) {
        setCollection(null);
      }
      // Refresh list
      loadCollections();
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      onAlertClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error deleting collection',
        description: error?.message || 'Could not delete the collection',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  // Dark mode aware colors
  const overlayBg = useColorModeValue('blackAlpha.300', 'blackAlpha.600');
  const contentBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.500', 'gray.400');
  const inputBg = useColorModeValue('white', 'gray.700');
  const inputBorderColor = useColorModeValue('gray.300', 'gray.600');
  const cardBg = useColorModeValue('white', 'gray.700');
  const selectedCardBg = useColorModeValue('blue.50', 'blue.900');
  const cardBorderColor = useColorModeValue('gray.200', 'gray.600');

  const loadCollections = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/collections');
      setCollections(response.data);
    } catch (error) {
      console.error('Failed to load collections:', error);
      toast({
        title: 'Error loading collections',
        description: 'Could not fetch collection list from server',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      // Fallback to empty array on error
      setCollections([]);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (isOpen) {
      loadCollections();
    }
  }, [isOpen, loadCollections]);

  const createCollection = async () => {
    if (!newCollectionName.trim()) {
      toast({
        title: 'Collection name required',
        description: 'Please enter a name for the new collection',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setCreating(true);
      const newName = newCollectionName.trim();
      
      // Create collection via API
      await api.post('/api/v1/collections', {
        collection_name: newName
      });
      
      // Update local state
      setCollections(prev => [...prev, newName]);
      setNewCollectionName('');
      
      toast({
        title: 'Collection created',
        description: `Collection "${newName}" has been created successfully`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error('Failed to create collection:', error);
      toast({
        title: 'Error creating collection',
        description: 'Could not create the collection. Please try again.',
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
      // Call API to select collection
      await api.post('/api/v1/collections/select', {
        collection_name: collectionName
      });
      
      // Update local state
      setCollection(collectionName);
      toast({
        title: 'Collection selected',
        description: `Now using collection: ${collectionName}`,
        status: 'success',
        duration: 2000,
        isClosable: true,
      });
      onClose();
    } catch (error) {
      console.error('Failed to select collection:', error);
      toast({
        title: 'Error selecting collection',
        description: 'Could not select the collection. Please try again.',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !creating) {
      createCollection();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay bg={overlayBg} />
      <ModalContent bg={contentBg}>
        <ModalHeader color={textColor}>Manage Collections</ModalHeader>
        <ModalCloseButton color={textColor} />
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {/* Create New Collection */}
            <Box>
              <Text fontWeight="semibold" mb={3} color={textColor}>Create New Collection</Text>
              <HStack spacing={3}>
                <Input
                  placeholder="Enter collection name..."
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  onKeyPress={handleKeyPress}
                  isDisabled={creating}
                  bg={inputBg}
                  borderColor={inputBorderColor}
                  color={textColor}
                  _placeholder={{ color: mutedTextColor }}
                  _focus={{
                    borderColor: 'blue.500',
                    boxShadow: '0 0 0 1px blue.500',
                  }}
                />
                <Button
                  colorScheme="blue"
                  onClick={createCollection}
                  isLoading={creating}
                  isDisabled={!newCollectionName.trim()}
                  loadingText="Creating..."
                >
                  Create
                </Button>
              </HStack>
            </Box>

            {/* Existing Collections */}
            <Box>
              <Text fontWeight="semibold" mb={2} color={textColor}>Existing Collections</Text>
              {loading ? (
                <Box textAlign="center" py={4}>
                  <Spinner color="blue.500" />
                </Box>
              ) : collections.length === 0 ? (
                <Text color={mutedTextColor} textAlign="center" py={4}>
                  No collections found. Create one above.
                </Text>
              ) : (
                <VStack spacing={2} align="stretch">
                  {collections.map((col) => (
                    <HStack
                      key={col}
                      p={3}
                      border="1px"
                      borderColor={cardBorderColor}
                      borderRadius="md"
                      justify="space-between"
                      bg={collection === col ? selectedCardBg : cardBg}
                      transition="all 0.2s"
                      _hover={{ shadow: 'sm' }}
                    >
                      <HStack spacing={3} align="center">
                        <Text color={textColor}>{col}</Text>
                        {collection === col && (
                          <Badge colorScheme="blue" size="sm">Active</Badge>
                        )}
                      </HStack>
                      <HStack spacing={2}>
                        <Button
                          size="sm"
                          colorScheme="blue"
                          variant={collection === col ? 'solid' : 'outline'}
                          onClick={() => selectCollection(col)}
                          isDisabled={collection === col}
                        >
                          {collection === col ? 'Selected' : 'Select'}
                        </Button>
                        <Tooltip label={`Delete ${col}`} placement="top">
                          <IconButton
                            aria-label={`Delete ${col}`}
                            icon={<FiTrash2 />}
                            size="sm"
                            variant="ghost"
                            colorScheme="red"
                            onClick={() => {
                              setCollectionToDelete(col);
                              onAlertOpen();
                            }}
                          />
                        </Tooltip>
                      </HStack>
                    </HStack>
                  ))}
                </VStack>
              )}
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button onClick={onClose} color={textColor} variant="ghost">Close</Button>
        </ModalFooter>

        <AlertDialog isOpen={isAlertOpen} leastDestructiveRef={null} onClose={onAlertClose}>
          <AlertDialogOverlay>
            <AlertDialogContent>
              <AlertDialogHeader fontSize="lg" fontWeight="bold">
                Delete Collection
              </AlertDialogHeader>
              <AlertDialogBody>
                Are you sure you want to delete collection{' '}
                <Text as="span" fontWeight="bold">{collectionToDelete}</Text>? This action cannot be undone.
              </AlertDialogBody>
              <AlertDialogFooter>
                <Button onClick={onAlertClose} mr={3} variant="ghost">
                  Cancel
                </Button>
                <Button colorScheme="red" onClick={() => collectionToDelete && deleteMutation.mutate(collectionToDelete)} isLoading={deleteMutation.isPending}>
                  Delete
                </Button>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialogOverlay>
        </AlertDialog>
      </ModalContent>
    </Modal>
  );
} 