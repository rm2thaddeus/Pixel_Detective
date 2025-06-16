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
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  InputGroup,
  InputLeftElement,
} from '@chakra-ui/react';
import { useState, useRef } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { FiFolder, FiUploadCloud, FiServer } from 'react-icons/fi';
import { useMutation } from '@tanstack/react-query';

interface AddImagesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type IngestVariables = { type: 'upload'; files: FileList } | { type: 'path'; path: string };

const startIngestion = async (variables: IngestVariables) => {
  if (variables.type === 'upload') {
    const formData = new FormData();
    Array.from(variables.files).forEach(file => {
      formData.append('files', file);
    });
    const { data } = await api.post('/api/v1/ingest/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  } else {
    const { data } = await api.post('/api/v1/ingest/scan', { directory_path: variables.path });
    return data;
  }
};

export function AddImagesModal({ isOpen, onClose }: AddImagesModalProps) {
  const { collection } = useStore();
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [serverPath, setServerPath] = useState('');
  const [tabIndex, setTabIndex] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const router = useRouter();

  const dropzoneBorder = useColorModeValue('gray.300', 'gray.600');
  const dropzoneBg = useColorModeValue('gray.50', 'gray.800');
  const dropzoneBgHover = useColorModeValue('gray.100', 'gray.700');
  const selectedBg = useColorModeValue('gray.100', 'gray.700');

  const mutation = useMutation({
    mutationFn: startIngestion,
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
    if (tabIndex === 0 && selectedFiles) {
      mutation.mutate({ type: 'upload', files: selectedFiles });
    } else if (tabIndex === 1 && serverPath) {
      mutation.mutate({ type: 'path', path: serverPath });
    }
  };

  const handleClose = () => {
    setSelectedFiles(null);
    setServerPath('');
    setTabIndex(0);
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
          <Tabs index={tabIndex} onChange={(index) => setTabIndex(index)}>
            <TabList>
              <Tab>Upload from this Computer</Tab>
              <Tab>Ingest from Server Path</Tab>
            </TabList>
            <TabPanels>
              <TabPanel>
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
                    <HStack w="full" bg={selectedBg} p={3} borderRadius="md">
                      <Icon as={FiFolder} />
                      <Text fontSize="sm" isTruncated>
                        {selectedFiles.length} file(s) selected from folder.
                      </Text>
                    </HStack>
                  )}
                </VStack>
              </TabPanel>
              <TabPanel>
                <VStack spacing={4}>
                    <Text>Provide a full directory path on the server where the application is running. The system will scan this directory for images.</Text>
                    <InputGroup>
                        <InputLeftElement pointerEvents='none'>
                            <Icon as={FiServer} color='gray.500' />
                        </InputLeftElement>
                        <Input 
                            placeholder="/path/to/images/on/server"
                            value={serverPath}
                            onChange={(e) => setServerPath(e.target.value)}
                        />
                    </InputGroup>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
          
          {mutation.isPending && (
            <VStack w="full" pt={4}>
              <Progress size="xs" isIndeterminate w="full" />
              <Text fontSize="sm" color="gray.500">Uploading...</Text>
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={handleClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleUpload}
            isDisabled={mutation.isPending || (tabIndex === 0 && !selectedFiles) || (tabIndex === 1 && !serverPath)}
            isLoading={mutation.isPending}
          >
            Start Ingestion
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 