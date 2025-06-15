'use client';

import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  VStack,
  Text,
  useToast,
  useColorModeValue,
  Box,
  Icon,
  Input,
  Progress,
  HStack,
} from '@chakra-ui/react';
import { useState, useRef } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { FiFolder, FiUploadCloud } from 'react-icons/fi';
import { useMutation } from '@tanstack/react-query';

interface AddImagesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const uploadFiles = async (files: FileList) => {
  const formData = new FormData();
  Array.from(files).forEach(file => {
    formData.append('files', file);
  });

  const { data } = await api.post('/api/v1/ingest/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
};

export function AddImagesModal({ isOpen, onClose }: AddImagesModalProps) {
  const { collection } = useStore();
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const router = useRouter();

  const dropzoneBorder = useColorModeValue('gray.300', 'gray.600');
  const dropzoneBg = useColorModeValue('gray.50', 'gray.800');
  const dropzoneBgHover = useColorModeValue('gray.100', 'gray.700');

  const mutation = useMutation({
    mutationFn: uploadFiles,
    onSuccess: (data) => {
      toast({
        title: 'Upload successful',
        description: `Ingestion job started with ID: ${data.job_id}`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      router.push(`/logs/${data.job_id}`);
      handleClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Upload failed',
        description: error.response?.data?.detail || 'An unexpected error occurred.',
        status: 'error',
        duration: 9000,
        isClosable: true,
      });
    },
  });

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      setSelectedFiles(event.target.files);
    }
  };

  const handleUpload = () => {
    if (!collection) {
      toast({ title: 'No collection selected', status: 'warning' });
      return;
    }
    if (selectedFiles) {
      mutation.mutate(selectedFiles);
    }
  };

  const handleClose = () => {
    setSelectedFiles(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    mutation.reset();
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Add Images to &quot;{collection}&quot;</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <Text>Select a folder containing your images to upload and ingest them into the current collection.</Text>
            <Box
              p={6}
              border="2px dashed"
              borderColor={dropzoneBorder}
              borderRadius="md"
              w="full"
              textAlign="center"
              bg={dropzoneBg}
              _hover={{ bg: dropzoneBgHover }}
              cursor="pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <VStack>
                <Icon as={FiUploadCloud} boxSize={12} color="gray.500" />
                <Text fontWeight="medium">Click to select a folder</Text>
                <Text fontSize="sm" color="gray.500">
                  You will be prompted to select a directory from your computer.
                </Text>
              </VStack>
              <Input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                style={{ display: 'none' }}
                {...{ webkitdirectory: 'true', mozdirectory: 'true' }}
              />
            </Box>
            {selectedFiles && (
              <HStack w="full" bg={useColorModeValue('gray.100', 'gray.700')} p={3} borderRadius="md">
                <Icon as={FiFolder} />
                <Text fontSize="sm" isTruncated>
                  {selectedFiles.length} file(s) selected from folder.
                </Text>
              </HStack>
            )}
            {mutation.isPending && (
              <VStack w="full">
                <Progress size="xs" isIndeterminate w="full" />
                <Text fontSize="sm" color="gray.500">Uploading...</Text>
              </VStack>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={handleClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleUpload}
            isDisabled={!selectedFiles || mutation.isPending}
            isLoading={mutation.isPending}
          >
            Upload and Ingest
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 