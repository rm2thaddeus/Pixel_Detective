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
  useToast,
  FormControl,
  FormLabel,
  FormHelperText,
  useColorModeValue,
  Code,
  Badge,
  Alert,
  AlertIcon,
  InputGroup
} from '@chakra-ui/react';
import { useState, useRef } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface AddImagesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AddImagesModal({ isOpen, onClose }: AddImagesModalProps) {
  const { collection } = useStore();
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Dark mode aware colors
  const overlayBg = useColorModeValue('blackAlpha.300', 'blackAlpha.600');
  const contentBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');
  const inputBg = useColorModeValue('white', 'gray.700');
  const inputBorderColor = useColorModeValue('gray.300', 'gray.600');
  const codeBg = useColorModeValue('gray.100', 'gray.700');
  const dropzoneBorder = useColorModeValue('gray.300', 'gray.600');
  const dropzoneBg = useColorModeValue('gray.50', 'gray.700');

  const startIngestion = async () => {
    if (!collection) {
      toast({
        title: 'No collection selected',
        description: 'Please select a collection first',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    if (!selectedFiles || selectedFiles.length === 0) {
      toast({
        title: 'No files selected',
        description: 'Please select one or more image files to upload.',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setLoading(true);
      
      // TODO: Implement multipart/form-data upload
      // const formData = new FormData();
      // Array.from(selectedFiles).forEach(file => {
      //   formData.append('files', file);
      // });
      // const response = await api.post('/api/v1/ingest/upload/', formData, { ... });

      // For now, we'll just simulate the success and log to console.
      console.log('Selected files:', selectedFiles);
      
      toast({
        title: 'Upload (Not Implemented)',
        description: `This feature is being refactored. ${selectedFiles.length} files are ready.`,
        status: 'info',
        duration: 5000,
        isClosable: true,
      });

      // onClose();
      // setDirectoryPath('');
      // router.push(`/logs/${response.data.job_id}`);

    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'response' in error && 
        error.response && typeof error.response === 'object' && 'data' in error.response &&
        error.response.data && typeof error.response.data === 'object' && 'detail' in error.response.data
        ? String(error.response.data.detail) 
        : 'Could not start ingestion';
      
      toast({
        title: 'Error starting ingestion',
        description: errorMessage,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setSelectedFiles(null);
      onClose();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(e.target.files);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="xl">
      <ModalOverlay bg={overlayBg} />
      <ModalContent bg={contentBg}>
        <ModalHeader color={textColor}>Add Images to Collection</ModalHeader>
        <ModalCloseButton isDisabled={loading} color={textColor} />
        
        <ModalBody>
          <VStack spacing={6} align="stretch">
            {collection ? (
              <HStack>
                <Text color="blue.500" fontWeight="semibold">
                  Adding to collection:
                </Text>
                <Badge colorScheme="blue">{collection}</Badge>
              </HStack>
            ) : (
              <Alert status="warning" size="sm">
                <AlertIcon />
                <Text fontSize="sm">No collection selected. Please select a collection first.</Text>
              </Alert>
            )}

            <FormControl>
              <FormLabel color={textColor}>Upload Images</FormLabel>
              <VStack
                p={5}
                border="2px dashed"
                borderColor={dropzoneBorder}
                borderRadius="md"
                bg={dropzoneBg}
                textAlign="center"
                cursor="pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <Input
                  type="file"
                  ref={fileInputRef}
                  multiple
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                  accept="image/jpeg,image/png,image/webp,image/gif,image/tiff,.dng,.cr2,.nef,.arw,.rw2,.orf"
                />
                <Text color={mutedTextColor}>
                  Drag & drop files here, or click to select files
                </Text>
                <FormHelperText color={mutedTextColor}>
                  Supported formats: JPG, PNG, DNG, TIFF, WEBP, and more.
                </FormHelperText>
              </VStack>
            </FormControl>

            {selectedFiles && selectedFiles.length > 0 && (
              <VStack align="start" spacing={1}>
                <Text fontSize="sm" fontWeight="semibold">{selectedFiles.length} files selected:</Text>
                <VStack align="start" spacing={0} pl={2} maxH="100px" overflowY="auto">
                {Array.from(selectedFiles).map((file, i) => (
                  <Text key={i} fontSize="xs" color={mutedTextColor}>{file.name}</Text>
                ))}
                </VStack>
              </VStack>
            )}

            <Alert status="info" size="sm">
              <AlertIcon />
              <Text fontSize="sm">
                The application will process all uploaded image files and add them to the selected collection.
              </Text>
            </Alert>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button 
            variant="ghost" 
            mr={3} 
            onClick={handleClose}
            isDisabled={loading}
            color={textColor}
          >
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={startIngestion}
            isLoading={loading}
            loadingText="Starting..."
            isDisabled={!collection || !selectedFiles || selectedFiles.length === 0}
          >
            Start Ingestion
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 