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
  AlertIcon
} from '@chakra-ui/react';
import { useState } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface AddImagesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AddImagesModal({ isOpen, onClose }: AddImagesModalProps) {
  const { collection } = useStore();
  const [directoryPath, setDirectoryPath] = useState('');
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const router = useRouter();

  // Dark mode aware colors
  const overlayBg = useColorModeValue('blackAlpha.300', 'blackAlpha.600');
  const contentBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');
  const inputBg = useColorModeValue('white', 'gray.700');
  const inputBorderColor = useColorModeValue('gray.300', 'gray.600');
  const codeBg = useColorModeValue('gray.100', 'gray.700');
  const buttonHoverBg = useColorModeValue('gray.50', 'gray.700');

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

    if (!directoryPath.trim()) {
      toast({
        title: 'Invalid path',
        description: 'Please enter a directory path',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    try {
      setLoading(true);
      const response = await api.post<{ job_id: string }>('/api/v1/ingest/', {
        directory_path: directoryPath.trim()
      });

      toast({
        title: 'Ingestion started',
        description: `Job ${response.data.job_id} has been started`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      onClose();
      setDirectoryPath('');
      
      // Navigate to logs page
      router.push(`/logs/${response.data.job_id}`);
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
      setDirectoryPath('');
      onClose();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      startIngestion();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} size="md">
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
              <FormLabel color={textColor}>Directory Path</FormLabel>
              <VStack spacing={3} align="stretch">
                <HStack spacing={2}>
                  <Input
                    placeholder="e.g., C:\\Users\\username\\Pictures\\my-images"
                    value={directoryPath}
                    onChange={(e) => setDirectoryPath(e.target.value)}
                    onKeyPress={handleKeyPress}
                    isDisabled={loading}
                    bg={inputBg}
                    borderColor={inputBorderColor}
                    color={textColor}
                    _placeholder={{ color: mutedTextColor }}
                    _focus={{
                      borderColor: 'blue.500',
                      boxShadow: '0 0 0 1px blue.500',
                    }}
                    flex="1"
                  />
                  <Button
                    size="md"
                    variant="outline"
                    onClick={() => document.getElementById('folder-input')?.click()}
                    isDisabled={loading}
                    borderColor={inputBorderColor}
                    color={textColor}
                    _hover={{
                      bg: buttonHoverBg,
                    }}
                  >
                    Browse
                  </Button>
                  <input
                    id="folder-input"
                    type="file"
                    style={{ display: 'none' }}
                    // @ts-expect-error - webkitdirectory is not in the types but is widely supported
                    webkitdirectory=""
                    directory=""
                    multiple
                    onChange={(e) => {
                      const files = e.target.files;
                      if (files && files.length > 0) {
                        // Get the directory path from the first file
                        const firstFile = files[0];
                        const fullPath = firstFile.webkitRelativePath || firstFile.name;
                        const dirPath = fullPath.split('/').slice(0, -1).join('/');
                        
                        // For local files, we can't get the full system path
                        // But we can provide a helpful message
                        if (dirPath) {
                          setDirectoryPath(`Selected: ${files.length} files from '${dirPath}'`);
                        } else {
                          setDirectoryPath(`Selected: ${files.length} files`);
                        }
                      }
                    }}
                  />
                </HStack>
                
                <FormHelperText color={mutedTextColor}>
                  Type the full directory path or click &quot;Browse&quot; to select a folder.
                  Supported formats: JPG, PNG, DNG, and more.
                </FormHelperText>
              </VStack>
            </FormControl>

            <VStack spacing={2} align="stretch">
              <Text fontSize="sm" fontWeight="semibold" color={textColor}>
                Quick Examples:
              </Text>
              <VStack spacing={1} align="stretch" pl={2}>
                <HStack>
                  <Text fontSize="xs" color={mutedTextColor} w="60px">Windows:</Text>
                  <Code bg={codeBg} color={textColor} fontSize="xs">{'C:\\Users\\yourname\\Pictures\\vacation'}</Code>
                </HStack>
                <HStack>
                  <Text fontSize="xs" color={mutedTextColor} w="60px">macOS:</Text>
                  <Code bg={codeBg} color={textColor} fontSize="xs">/Users/yourname/Pictures/vacation</Code>
                </HStack>
                <HStack>
                  <Text fontSize="xs" color={mutedTextColor} w="60px">Linux:</Text>
                  <Code bg={codeBg} color={textColor} fontSize="xs">/home/yourname/Pictures/vacation</Code>
                </HStack>
              </VStack>
            </VStack>
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
            isDisabled={!collection || !directoryPath.trim()}
          >
            Start Ingestion
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 