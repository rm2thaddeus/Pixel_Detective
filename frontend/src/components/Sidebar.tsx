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
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useToast,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2, FiRefreshCw } from 'react-icons/fi';
import { useStore } from '@/store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import React from 'react';

interface SidebarProps {
  onOpenCollectionModal: () => void;
}

const fetchCollections = async () => {
  const { data } = await api.get<string[]>('/api/v1/collections');
  return data;
};

const deleteCollection = async (collectionName: string) => {
  await api.delete(`/api/v1/collections/${collectionName}`);
};

export function Sidebar({ onOpenCollectionModal }: SidebarProps) {
  const { collection, setCollection } = useStore();
  const { data: collections, isLoading, refetch } = useQuery({
    queryKey: ['collections'],
    queryFn: fetchCollections,
  });
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedForDeletion, setSelectedForDeletion] = React.useState<string | null>(null);
  const cancelRef = React.useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const mutation = useMutation({
    mutationFn: deleteCollection,
    onSuccess: (_, deletedCollectionName) => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      toast({
        title: 'Collection deleted.',
        description: `Successfully deleted '${deletedCollectionName}'.`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      // If the active collection was deleted, clear it from the store
      if (collection === deletedCollectionName) {
        setCollection(null);
      }
    },
    onError: (error: any, deletedCollectionName) => {
      toast({
        title: 'Deletion failed.',
        description: error.response?.data?.detail || `Could not delete '${deletedCollectionName}'.`,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
    onSettled: () => {
      handleCloseDialog();
    }
  });

  const sidebarBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const handleDeleteClick = (collectionName: string) => {
    setSelectedForDeletion(collectionName);
    onOpen();
  };

  const handleConfirmDelete = () => {
    if (selectedForDeletion) {
      mutation.mutate(selectedForDeletion);
    }
  };

  const handleCloseDialog = () => {
    setSelectedForDeletion(null);
    onClose();
  };

  return (
    <>
      <Box
        as="aside"
        w="280px"
        bg={sidebarBg}
        borderRight="1px"
        borderColor={borderColor}
        p={4}
        h="100vh"
        position="sticky"
        top={0}
      >
        <VStack spacing={4} align="stretch">
          <HStack justify="space-between" align="center">
            <Heading size="md">Collections</Heading>
            <Tooltip label="Refresh list" placement="top">
              <IconButton
                aria-label="Refresh collections"
                icon={<FiRefreshCw />}
                size="sm"
                variant="ghost"
                onClick={() => refetch()}
                isLoading={isLoading}
              />
            </Tooltip>
          </HStack>
          <Divider />
          <VStack spacing={2} align="stretch" overflowY="auto" flex="1">
            {isLoading ? (
              <Text>Loading...</Text>
            ) : (
              collections?.map((c) => (
                <HStack
                  key={c}
                  p={2}
                  borderRadius="md"
                  bg={collection === c ? 'blue.500' : 'transparent'}
                  color={collection === c ? 'white' : 'inherit'}
                  cursor="pointer"
                  onClick={() => setCollection(c)}
                  justifyContent="space-between"
                  _hover={{ bg: collection !== c ? useColorModeValue('gray.100', 'gray.700') : 'blue.600' }}
                >
                  <Text isTruncated>{c}</Text>
                  <Tooltip label={`Delete ${c}`} placement="top">
                    <IconButton
                      aria-label={`Delete ${c}`}
                      icon={<FiTrash2 />}
                      size="xs"
                      variant="ghost"
                      colorScheme="red"
                      onClick={(e) => {
                        e.stopPropagation(); // Prevent collection selection
                        handleDeleteClick(c);
                      }}
                      visibility={collection === c ? 'visible' : 'hidden'}
                      _groupHover={{ visibility: 'visible' }}
                    />
                  </Tooltip>
                </HStack>
              ))
            )}
          </VStack>
          <Button
            leftIcon={<FiPlus />}
            onClick={onOpenCollectionModal}
            colorScheme="blue"
          >
            New Collection
          </Button>
        </VStack>
      </Box>

      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={handleCloseDialog}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Collection
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete the collection{' '}
              <Text as="span" fontWeight="bold">{selectedForDeletion}</Text>? This action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={handleCloseDialog}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleConfirmDelete}
                ml={3}
                isLoading={mutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </>
  );
} 