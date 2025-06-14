'use client';

import { useState, useRef, useCallback } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  Text,
  SimpleGrid,
  Image,
  Card,
  CardBody,
  Badge,
  Alert,
  AlertIcon,
  Spinner,
  InputGroup,
  InputRightElement,
  useColorModeValue,
  IconButton,
  useToast,
  AspectRatio,
  Flex,
  Icon,
  Center
} from '@chakra-ui/react';
import { FiUpload, FiX, FiSearch, FiImage, FiType } from 'react-icons/fi';
import { Header } from '@/components/Header';
import { useStore } from '@/store/useStore';
import { api, mlApi } from '@/lib/api';

interface SearchResult {
  id: string;
  filename: string;
  caption?: string;
  score: number;
  thumbnail_url?: string;
  payload?: Record<string, unknown>;
}

interface SearchResponse {
  total_approx: number;
  page: number;
  per_page: number;
  results: SearchResult[];
  query: string;
  embedding_model?: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [searchType, setSearchType] = useState<'text' | 'image' | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();
  const { collection } = useStore();

  // All color mode values at top level to avoid Hook rule violations
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBorderColor = useColorModeValue('blue.300', 'blue.500');
  const dragBorderColor = useColorModeValue('blue.500', 'blue.300');
  const pageBg = useColorModeValue('gray.50', 'gray.900');
  const headerText = useColorModeValue('gray.600', 'gray.400');
  const cardPreviewBg = useColorModeValue('gray.50', 'gray.700');
  const captionText = useColorModeValue('gray.600', 'gray.400');
  const fallbackBg = useColorModeValue('gray.100', 'gray.700');
  const fallbackIconColor = useColorModeValue('gray.400', 'gray.500');
  const fallbackTextColor = useColorModeValue('gray.500', 'gray.400');
  const noResultsIconColor = useColorModeValue('gray.400', 'gray.500');
  const noResultsText = useColorModeValue('gray.600', 'gray.400');

  // Handle file selection
  const handleFileSelect = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Invalid file type',
        description: 'Please select an image file (JPG, PNG, GIF, etc.)',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setSelectedImage(file);
    setSearchType('image');
    setQuery(`🖼️ ${file.name}`);
    
    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, [toast]);

  // Handle drag and drop
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  // Clear image selection
  const clearImage = useCallback(() => {
    setSelectedImage(null);
    setImagePreview(null);
    setSearchType(null);
    setQuery('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // Handle text input change
  const handleTextChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    
    if (value.trim() && !selectedImage) {
      setSearchType('text');
    } else if (!value.trim() && !selectedImage) {
      setSearchType(null);
    }
  }, [selectedImage]);

  // Perform search
  const handleSearch = async () => {
    if (!query.trim() && !selectedImage) {
      toast({
        title: 'Search query required',
        description: 'Please enter text or select an image to search',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

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

    setLoading(true);
    setResults([]);

    try {
      if (selectedImage) {
        // Image search
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            const base64Image = e.target?.result as string;
            
            // Get embedding from ML service
            const embedResponse = await mlApi.post('/api/v1/embed', {
              image_base64: base64Image.split(',')[1],
              filename: selectedImage.name
            });

            // Search using the embedding
            const searchResponse = await api.post<SearchResponse>('/api/v1/search', {
              embedding: embedResponse.data.embedding,
              limit: 20,
              offset: 0
            });

            setResults(searchResponse.data.results || []);
            setTotalResults(searchResponse.data.total_approx || 0);
            
            toast({
              title: 'Image search completed',
              description: `Found ${searchResponse.data.results?.length || 0} similar images`,
              status: 'success',
              duration: 3000,
              isClosable: true,
            });
          } catch (error) {
            console.error('Image search error:', error);
            toast({
              title: 'Image search failed',
              description: 'Could not process the image. Please try again.',
              status: 'error',
              duration: 5000,
              isClosable: true,
            });
          } finally {
            setLoading(false);
          }
        };
        reader.readAsDataURL(selectedImage);
      } else {
        // Text search
        const searchResponse = await api.post<SearchResponse>('/api/v1/search/text', {
          text: query.trim(),
          limit: 20,
          offset: 0
        });

        setResults(searchResponse.data.results || []);
        setTotalResults(searchResponse.data.total_approx || 0);
        
        toast({
          title: 'Text search completed',
          description: `Found ${searchResponse.data.results?.length || 0} matching images`,
          status: 'success',
          duration: 3000,
          isClosable: true,
        });
        setLoading(false);
      }
    } catch (error) {
      console.error('Search error:', error);
      toast({
        title: 'Search failed',
        description: 'Could not complete the search. Please try again.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      setLoading(false);
    }
  };

  // Handle Enter key
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box minH="100vh" bg={pageBg}>
      <Header />
      
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
                {/* Main Search Input */}
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
                      transition="all 0.2s"
                    />
                    <InputRightElement width="110px" pr={2}>
                      <HStack spacing={1}>
                        {/* Search Type Indicator */}
                        {searchType && (
                          <Badge
                            colorScheme={searchType === 'text' ? 'blue' : 'green'}
                            variant="subtle"
                            fontSize="xs"
                          >
                            <Icon as={searchType === 'text' ? FiType : FiImage} mr={1} />
                            {searchType}
                          </Badge>
                        )}
                        
                        {/* File Upload Button */}
                        <IconButton
                          aria-label="Upload image"
                          icon={<FiUpload />}
                          size="sm"
                          variant="ghost"
                          onClick={() => fileInputRef.current?.click()}
                        />
                        
                        {/* Search Button */}
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

                  {/* Hidden File Input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileInputChange}
                    style={{ display: 'none' }}
                  />

                  {/* Drag Overlay */}
                  {isDragOver && (
                    <Box
                      position="absolute"
                      top={0}
                      left={0}
                      right={0}
                      bottom={0}
                      bg="blue.500"
                      opacity={0.1}
                      borderRadius="md"
                      border="2px dashed"
                      borderColor="blue.500"
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      pointerEvents="none"
                    >
                      <Text color="blue.500" fontWeight="bold">
                        Drop image here to search
                      </Text>
                    </Box>
                  )}
                </Box>

                {/* Image Preview */}
                {imagePreview && (
                  <HStack spacing={4} w="full" p={4} bg={cardPreviewBg} borderRadius="md">
                    <AspectRatio ratio={1} w="60px">
                      <Image
                        src={imagePreview}
                        alt="Selected image"
                        borderRadius="md"
                        objectFit="cover"
                      />
                    </AspectRatio>
                    <VStack align="start" flex={1} spacing={1}>
                      <Text fontSize="sm" fontWeight="medium">
                        Selected Image: {selectedImage?.name}
                      </Text>
                      <Text fontSize="xs" color={captionText}>
                        Ready to search for similar images
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

                {/* Collection Status */}
                {collection && (
                  <Alert status="info" borderRadius="md">
                    <AlertIcon />
                    <Text fontSize="sm">
                      Searching in collection: <strong>{collection}</strong>
                    </Text>
                  </Alert>
                )}
              </VStack>
            </CardBody>
          </Card>

          {/* Search Results */}
          {(results.length > 0 || loading) && (
            <VStack spacing={6} align="stretch">
              {/* Results Header */}
              {!loading && results.length > 0 && (
                <Flex justify="space-between" align="center">
                  <Text fontSize="lg" fontWeight="medium">
                    Found {totalResults} results
                  </Text>
                  <Badge colorScheme="blue" variant="subtle">
                    {searchType === 'image' ? 'Similar Images' : 'Text Search'}
                  </Badge>
                </Flex>
              )}

              {/* Loading State */}
              {loading && (
                <Center py={12}>
                  <VStack spacing={4}>
                    <Spinner size="xl" color="blue.500" />
                    <Text>
                      {searchType === 'image' ? 'Finding similar images...' : 'Searching images...'}
                    </Text>
                  </VStack>
                </Center>
              )}

              {/* Results Grid */}
              {!loading && results.length > 0 && (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3, xl: 4 }} spacing={6}>
                  {results.map((result) => (
                    <Card key={result.id} overflow="hidden" _hover={{ transform: 'translateY(-2px)', shadow: 'lg' }} transition="all 0.2s">
                      <AspectRatio ratio={1}>
                        <Image
                          src={result.thumbnail_url || `http://localhost:8002/api/v1/images/${result.id}/thumbnail`}
                          alt={result.caption || result.filename}
                          objectFit="cover"
                          onError={(e) => {
                            console.log('Image load error for:', result.id, result.filename);
                            // Try fallback URL
                            const img = e.target as HTMLImageElement;
                            if (!img.src.includes('/image/')) {
                              img.src = `http://localhost:8002/api/v1/images/${result.id}/image`;
                            }
                          }}
                          fallback={
                            <Center bg={fallbackBg} h="full">
                              <VStack spacing={2}>
                                <Icon as={FiImage} boxSize={8} color={fallbackIconColor} />
                                <Text fontSize="xs" color={fallbackTextColor}>
                                  {result.filename}
                                </Text>
                              </VStack>
                            </Center>
                          }
                        />
                      </AspectRatio>
                      <CardBody p={4}>
                        <VStack align="start" spacing={2}>
                          <Text fontSize="sm" fontWeight="medium" noOfLines={1}>
                            {result.filename}
                          </Text>
                          {result.caption && (
                            <Text fontSize="xs" color={captionText} noOfLines={2}>
                              {result.caption}
                            </Text>
                          )}
                          <Badge colorScheme="green" variant="subtle" fontSize="xs">
                            {Math.round(result.score * 100)}% match
                          </Badge>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
              )}

              {/* No Results */}
              {!loading && results.length === 0 && query && (
                <Center py={12}>
                  <VStack spacing={4} textAlign="center">
                    <Icon as={FiSearch} boxSize={12} color={noResultsIconColor} />
                    <Text fontSize="lg" fontWeight="medium">
                      No results found
                    </Text>
                    <Text color={noResultsText}>
                      Try different keywords or upload a different image
                    </Text>
                  </VStack>
                </Center>
              )}
            </VStack>
          )}
        </VStack>
      </Box>
    </Box>
  );
}