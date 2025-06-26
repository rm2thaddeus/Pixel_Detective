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
  Flex,
  Spinner,
} from '@chakra-ui/react';
import { FiPlus, FiTrash2, FiRefreshCw, FiGrid, FiHome, FiScatter } from 'react-icons/fi';
import { useStore } from '@/store/useStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, deleteCollection as deleteCollectionApi, selectCollection as selectCollectionApi } from '@/lib/api';
import React, { useState } from 'react';
import NextLink from 'next/link';

interface SidebarProps {
  onOpenCollectionModal: () => void;
}

const fetchCollections = async (): Promise<string[]> => {
  const response = await api.get('/api/v1/collections');
  return response.data;
};

const deleteCollection = deleteCollectionApi;

export function Sidebar({ onOpenCollectionModal }: SidebarProps) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [collectionToDelete, setCollectionToDelete] = useState<string | null>(null);
  const { isOpen: isAlertOpen, onOpen: onAlertOpen, onClose: onAlertClose } = useDisclosure();

  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: fetchCollections,
  });
  const activeCollection = useStore((state) => state.collection);
  const setActiveCollection = useStore((state) => state.setCollection);

  const mutation = useMutation({
    mutationFn: deleteCollection,
    onSuccess: () => {
      toast({
        title: 'Collection deleted.',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      if (collectionToDelete === activeCollection) {
        setActiveCollection('');
      }
      onAlertClose();
    },
    onError: (error) => {
      toast({
        title: 'Error deleting collection.',
        description: error.message,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const selectMutation = useMutation({
    mutationFn: (name: string) => selectCollectionApi(name),
    onError: (err: any) => {
      toast({
        title: 'Failed to select collection',
        description: err?.response?.data?.detail || err.message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    },
  });

  const handleDeleteClick = (collectionName: string) => {
    setCollectionToDelete(collectionName);
    onAlertOpen();
  };

  const handleConfirmDelete = () => {
    if (collectionToDelete) {
      mutation.mutate(collectionToDelete);
    }
  };

  const handleCloseDialog = () => {
    onAlertClose();
  };

  return (
    <Box
      as="nav"
      pos="fixed"
      top="0"
      left="0"
      zIndex="sticky"
      h="full"
      pb="10"
      overflowX="hidden"
      overflowY="auto"
      bg={useColorModeValue('white', 'gray.800')}
      borderColor={useColorModeValue('inherit', 'gray.700')}
      borderRightWidth="1px"
      w="60"
    >
      <Flex px="4" py="5" align="center">
        <Text
          fontSize="2xl"
          ml="2"
          color={useColorModeValue('brand.500', 'white')}
          fontWeight="semibold"
        >
          Vibe Coder
        </Text>
      </Flex>
      <Flex
        direction="column"
        as="nav"
        fontSize="sm"
        color="gray.600"
        aria-label="Main Navigation"
      >
        <Button as={NextLink} href="/" variant="ghost" leftIcon={<FiHome />} justifyContent="start" mb={2}>
            Home
        </Button>
        <Button as={NextLink} href="/collections" variant="ghost" leftIcon={<FiGrid />} justifyContent="start" mb={2}>
            Collections
        </Button>
        <Button as={NextLink} href="/latent-space" variant="ghost" leftIcon={<FiScatter />} justifyContent="start" mb={4}>
            Latent Space
        </Button>

        <HStack px={4} mb={2} justifyContent="space-between">
            <Text fontWeight="bold">My Collections</Text>
            <IconButton 
                aria-label="Create Collection" 
                icon={<FiPlus />} 
                size="sm"
                onClick={onOpenCollectionModal}
            />
        </HStack>
        {isLoading && <Spinner mx="auto" />}
        <VStack spacing={1} align="stretch">
          {collections?.map((name) => (
            <HStack
              key={name}
              p={2}
              borderRadius="md"
              bg={activeCollection === name ? 'blue.500' : 'transparent'}
              color={activeCollection === name ? 'white' : 'inherit'}
              cursor="pointer"
              onClick={() => {
                setActiveCollection(name);
                selectMutation.mutate(name);
              }}
              justifyContent="space-between"
              _hover={{ bg: activeCollection !== name ? useColorModeValue('gray.100', 'gray.700') : 'blue.600' }}
            >
              <Text isTruncated>{name}</Text>
              <Tooltip label={`Delete ${name}`} placement="top">
                <IconButton
                  aria-label={`Delete ${name}`}
                  icon={<FiTrash2 />}
                  size="xs"
                  variant="ghost"
                  colorScheme="red"
                  onClick={(e) => {
                    e.stopPropagation(); // Prevent collection selection
                    handleDeleteClick(name);
                  }}
                  visibility={activeCollection === name ? 'visible' : 'hidden'}
                  _groupHover={{ visibility: 'visible' }}
                />
              </Tooltip>
            </HStack>
          ))}
        </VStack>
      </Flex>

      <AlertDialog
        isOpen={isAlertOpen}
        leastDestructiveRef={null}
        onClose={handleCloseDialog}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Collection
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete the collection{' '}
              <Text as="span" fontWeight="bold">{collectionToDelete}</Text>? This action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button
                colorScheme="red"
                onClick={handleConfirmDelete}
                isLoading={mutation.isPending}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
} 