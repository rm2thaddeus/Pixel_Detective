'use client';

import React, { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  Input,
  InputGroup,
  InputRightElement,
  IconButton,
  Button,
  Card,
  CardBody,
  SimpleGrid,
  AspectRatio,
  Badge,
  Spinner,
  Center,
  Icon,
  Alert,
  AlertIcon,
  useColorModeValue,
  useToast,
  Flex,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Divider,
  Table,
  Tbody,
  Tr,
  Td,
  TableContainer,
} from '@chakra-ui/react';
import { FiSearch, FiImage, FiUpload, FiX, FiType, FiInfo, FiDownload } from 'react-icons/fi';
import { Header } from '@/components/Header';
import { api } from '@/lib/api';
import { ClientOnly } from '@/components/ClientOnly';
import NextImage from 'next/image';
import { useSearch, type SearchResult } from '@/hooks/useSearch';

interface ImageDetails {
  id: string;
  filename: string;
  full_path: string;
  caption?: string;
  file_hash: string;
  width: number;
  height: number;
  format: string;
  mode: string;
  has_thumbnail: boolean;
  exif?: Record<string, string>;
}

export default function SearchPage() {
  const {
    query,
    results,
    loading,
    searchType,
    imagePreview,
    selectedImage,
    fileInputRef,
    handleTextChange,
    handleSearch,
    handleImageSelection,
    clearImage,
  } = useSearch();

  const [collection, setCollection] = useState<string | null>(null);
  const [selectedImageDetails, setSelectedImageDetails] = useState<ImageDetails | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBorderColor = useColorModeValue('gray.300', 'gray.500');
  const dragBorderColor = useColorModeValue('blue.400', 'blue.300');
  const pageBg = useColorModeValue('gray.50', 'gray.900');
  const headerText = useColorModeValue('gray.600', 'gray.400');
  const cardPreviewBg = useColorModeValue('gray.100', 'gray.700');
  const noResultsIconColor = useColorModeValue('gray.300', 'gray.600');
  const noResultsText = useColorModeValue('gray.500', 'gray.400');

  React.useEffect(() => {
    api.get('/health')
      .then(response => {
        if (response.data?.active_collection) {
          setCollection(response.data.active_collection);
        }
      })
      .catch(error => console.error('Failed to fetch collection info:', error));
  }, []);

  const handleImageClick = async (result: SearchResult) => {
    try {
      const response = await api.get<ImageDetails>(`/api/v1/images/${result.id}/info`);
      setSelectedImageDetails(response.data);
      onOpen();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load image details',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImageSelection(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const imageFile = Array.from(e.dataTransfer.files).find(file => file.type.startsWith('image/'));
    if (imageFile) {
      handleImageSelection(imageFile);
    } else {
      toast({ title: 'Invalid file', description: 'Please drop an image file', status: 'error', duration: 3000 });
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <Box minH="100vh" bg={pageBg}>
      <ClientOnly>
        <Header />
      </ClientOnly>
      
      <Box maxW="6xl" mx="auto" p={6}>
        <VStack spacing={8} align="stretch">
          {/* Search Header */}
          <VStack spacing={4} textAlign="center">
            <Text fontSize="3xl" fontWeight="bold">
              🔍 Search Your Images
            </Text>
            <Text fontSize="lg" color={headerText}>
              Search by typing a description or drag & drop an image to find similar ones
            </Text>
          </VStack>

          {/* Unified Search Bar */}
          <Card>
            <CardBody>
              <VStack spacing={4}>
                <Box
                  w="full"
                  position="relative"
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <InputGroup size="lg">
                    <Input
                      placeholder="Search for images... or drag & drop an image here"
                      value={query}
                      onChange={handleTextChange}
                      onKeyPress={handleKeyPress}
                      bg={bgColor}
                      border="2px solid"
                      borderColor={isDragOver ? dragBorderColor : borderColor}
                      _hover={{ borderColor: hoverBorderColor }}
                      _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 1px blue.500' }}
                      pr="120px"
                      fontSize="md"
                    />
                    <InputRightElement width="110px" pr={2}>
                      <HStack spacing={1}>
                        {searchType && (
                          <Badge
                            colorScheme={searchType === 'text' ? 'blue' : 'green'}
                            variant="subtle"
                          >
                            <Icon as={searchType === 'text' ? FiType : FiImage} mr={1} />
                            {searchType}
                          </Badge>
                        )}
                        <IconButton
                          aria-label="Upload image"
                          icon={<FiUpload />}
                          size="sm"
                          variant="ghost"
                          onClick={() => fileInputRef.current?.click()}
                        />
                        <IconButton
                          aria-label="Search"
                          icon={loading ? <Spinner size="sm" /> : <FiSearch />}
                          size="sm"
                          colorScheme="blue"
                          onClick={handleSearch}
                          isLoading={loading}
                        />
                      </HStack>
                    </InputRightElement>
                  </InputGroup>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileInputChange}
                    style={{ display: 'none' }}
                  />
                </Box>

                {imagePreview && (
                  <HStack spacing={4} w="full" p={4} bg={cardPreviewBg} borderRadius="md">
                    <AspectRatio ratio={1} w="60px">
                      <NextImage
                        src={imagePreview}
                        alt="Selected image"
                        width={60}
                        height={60}
                        style={{ borderRadius: 'var(--chakra-radii-md)', objectFit: 'cover' }}
                      />
                    </AspectRatio>
                    <VStack align="start" flex={1} spacing={1}>
                      <Text fontSize="sm" fontWeight="medium">
                        Selected: {selectedImage?.name}
                      </Text>
                    </VStack>
                    <IconButton
                      aria-label="Remove image"
                      icon={<FiX />}
                      size="sm"
                      variant="ghost"
                      onClick={clearImage}
                    />
                  </HStack>
                )}

                {collection && (
                  <Alert status="info" borderRadius="md">
                    <AlertIcon />
                    <Text fontSize="sm">Searching in collection: <strong>{collection}</strong></Text>
                  </Alert>
                )}
              </VStack>
            </CardBody>
          </Card>

          {/* Search Results */}
          {(results.length > 0 || loading) && (
            <VStack spacing={6} align="stretch">
              {loading && (
                <Center py={12}>
                  <VStack spacing={4}>
                    <Spinner size="xl" color="blue.500" />
                    <Text>Searching...</Text>
                  </VStack>
                </Center>
              )}

              {!loading && results.length > 0 && (
                <SimpleGrid columns={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing={6}>
                  {results.map((result) => (
                    result.payload?.filename && (
                      <Box
                        key={result.id}
                        onClick={() => handleImageClick(result)}
                        cursor="pointer"
                        borderWidth={2}
                        borderColor="transparent"
                        borderRadius="lg"
                        overflow="hidden"
                        position="relative"
                        _hover={{
                          borderColor: 'blue.500',
                          boxShadow: 'lg',
                        }}
                      >
                        <NextImage
                          src={`/api/v1/images/${result.id}/thumbnail`}
                          alt={result.payload.filename}
                          width={300}
                          height={300}
                          style={{ objectFit: 'cover', width: '100%', height: '250px' }}
                        />
                        <Box p={3} bg={cardPreviewBg}>
                          <Text fontSize="sm" isTruncated>
                            {result.payload.filename}
                          </Text>
                        </Box>
                      </Box>
                    )
                  ))}
                </SimpleGrid>
              )}

              {!loading && results.length === 0 && query && (
                <Center py={12}>
                  <VStack spacing={4} textAlign="center">
                    <Icon as={FiSearch} boxSize={12} color={noResultsIconColor} />
                    <Text fontSize="lg" fontWeight="medium">No results found</Text>
                    <Text color={noResultsText}>Try different keywords.</Text>
                  </VStack>
                </Center>
              )}
            </VStack>
          )}
        </VStack>
      </Box>

      {/* Image Details Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="4xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Image Details</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {selectedImageDetails && (
              <VStack spacing={6} align="stretch">
                <Center>
                  <AspectRatio ratio={selectedImageDetails.width / selectedImageDetails.height || 1} w="full" maxW="500px">
                    <NextImage
                      src={`/api/v1/images/${selectedImageDetails.id}/image`}
                      alt={selectedImageDetails.filename}
                      width={selectedImageDetails.width}
                      height={selectedImageDetails.height}
                      style={{ objectFit: 'contain', borderRadius: 'var(--chakra-radii-md)' }}
                    />
                  </AspectRatio>
                </Center>
                <Divider />
                <VStack align="stretch" spacing={4}>
                  <Text fontSize="lg" fontWeight="bold">Information</Text>
                  <TableContainer>
                    <Table size="sm">
                      <Tbody>
                        <Tr>
                          <Td fontWeight="medium">Filename</Td>
                          <Td>{selectedImageDetails.filename}</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="medium">Dimensions</Td>
                          <Td>{selectedImageDetails.width} × {selectedImageDetails.height}</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="medium">Format</Td>
                          <Td>{selectedImageDetails.format}</Td>
                        </Tr>
                        <Tr>
                          <Td fontWeight="medium">Color Mode</Td>
                          <Td>{selectedImageDetails.mode}</Td>
                        </Tr>
                        {selectedImageDetails.caption && (
                          <Tr>
                            <Td fontWeight="medium">Caption</Td>
                            <Td>{selectedImageDetails.caption}</Td>
                          </Tr>
                        )}
                        <Tr>
                          <Td fontWeight="medium">File Hash</Td>
                          <Td fontFamily="mono" fontSize="xs">{selectedImageDetails.file_hash}</Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </TableContainer>
                </VStack>
                {selectedImageDetails.exif && Object.keys(selectedImageDetails.exif).length > 0 && (
                  <>
                    <Divider />
                    <VStack align="stretch" spacing={4}>
                      <Text fontSize="lg" fontWeight="bold">EXIF Data</Text>
                      <TableContainer>
                        <Table size="sm">
                          <Tbody>
                            {Object.entries(selectedImageDetails.exif).map(([key, value]) => (
                              <Tr key={key}>
                                <Td fontWeight="medium">{key}</Td>
                                <Td>{value}</Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </TableContainer>
                    </VStack>
                  </>
                )}
              </VStack>
            )}
          </ModalBody>
          <ModalFooter>
            <Button
              leftIcon={<FiDownload />}
              colorScheme="blue"
              onClick={() => {
                if (selectedImageDetails) {
                  window.open(`/api/v1/images/${selectedImageDetails.id}/image`, '_blank');
                }
              }}
            >
              Download
            </Button>
            <Button variant="ghost" onClick={onClose}>Close</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}