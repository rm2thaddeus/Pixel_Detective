'use client';

import { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
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
  InputRightElement
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

interface SearchResult {
  filename: string;
  caption?: string;
  score: number;
  thumbnail_url?: string;
  file_path?: string;
}

export default function SearchPage() {
  const { collection } = useStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!collection) {
      return;
    }

    if (!query.trim()) {
      return;
    }

    try {
      setLoading(true);
      const response = await api.post<SearchResult[]>('/api/v1/search', {
        embedding: query.trim(),
        limit: 10
      });

      setResults(response.data);
      setHasSearched(true);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
      setHasSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleSearch();
    }
  };

  return (
    <Box>
      <Header />
      <Box p={8} maxW="6xl" mx="auto">
        <VStack spacing={6} align="stretch">
          {/* Search Header */}
          <Box textAlign="center">
            <Text fontSize="3xl" fontWeight="bold" mb={2}>
              Search Your Collection
            </Text>
            {collection ? (
              <Text color="blue.600" fontSize="lg">
                Searching in: {collection}
              </Text>
            ) : (
              <Alert status="warning" mb={4}>
                <AlertIcon />
                No collection selected. Please select a collection first.
              </Alert>
            )}
          </Box>

          {/* Search Input */}
          <Box maxW="2xl" mx="auto" w="full">
            <InputGroup size="lg">
              <Input
                placeholder="Describe what you're looking for... (e.g., 'sunset over mountains', 'red car', 'people laughing')"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                isDisabled={!collection || loading}
              />
              <InputRightElement width="4.5rem">
                <Button
                  h="1.75rem"
                  size="sm"
                  onClick={handleSearch}
                  isLoading={loading}
                  isDisabled={!collection || !query.trim()}
                  colorScheme="blue"
                >
                  Search
                </Button>
              </InputRightElement>
            </InputGroup>
          </Box>

          {/* Loading State */}
          {loading && (
            <Box textAlign="center" py={8}>
              <Spinner size="xl" color="blue.500" />
              <Text mt={4} color="gray.600">
                Searching through your images...
              </Text>
            </Box>
          )}

          {/* Results */}
          {!loading && hasSearched && (
            <Box>
              <HStack justify="space-between" align="center" mb={4}>
                <Text fontSize="xl" fontWeight="semibold">
                  Search Results
                </Text>
                <Badge colorScheme="blue" fontSize="sm">
                  {results.length} results
                </Badge>
              </HStack>

              {results.length === 0 ? (
                <Box textAlign="center" py={8}>
                  <Text fontSize="lg" color="gray.500">
                    No results found for &quot;{query}&quot;
                  </Text>
                  <Text color="gray.400" mt={2}>
                    Try different keywords or make sure your collection has images.
                  </Text>
                </Box>
              ) : (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  {results.map((result, index) => (
                    <Card key={index} overflow="hidden" shadow="md">
                      <Box position="relative">
                        <Image
                          src={result.thumbnail_url || '/placeholder-image.png'}
                          alt={result.filename}
                          objectFit="cover"
                          w="full"
                          h="200px"
                          bg="gray.100"
                          fallbackSrc="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjdmYWZjIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzY4NzI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg=="
                        />
                        <Badge
                          position="absolute"
                          top={2}
                          right={2}
                          colorScheme="blue"
                          variant="solid"
                        >
                          {Math.round(result.score * 100)}%
                        </Badge>
                      </Box>
                      <CardBody>
                        <VStack align="start" spacing={2}>
                          <Text fontWeight="semibold" fontSize="sm" noOfLines={1}>
                            {result.filename}
                          </Text>
                          {result.caption && (
                            <Text fontSize="xs" color="gray.600" noOfLines={2}>
                              {result.caption}
                            </Text>
                          )}
                          <HStack justify="space-between" w="full">
                            <Text fontSize="xs" color="gray.500">
                              Match: {Math.round(result.score * 100)}%
                            </Text>
                          </HStack>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
              )}
            </Box>
          )}

          {/* Search Tips */}
          {!hasSearched && (
            <Box bg="gray.50" p={6} borderRadius="md">
              <Text fontWeight="semibold" mb={3}>
                💡 Search Tips:
              </Text>
              <VStack align="start" spacing={1} fontSize="sm" color="gray.600">
                <Text>• Describe what you see: &quot;red car in parking lot&quot;</Text>
                <Text>• Use emotions: &quot;happy people&quot;, &quot;peaceful landscape&quot;</Text>
                <Text>• Try colors and objects: &quot;blue sky&quot;, &quot;wooden table&quot;</Text>
                <Text>• Be specific: &quot;dog running on beach&quot; vs just &quot;dog&quot;</Text>
              </VStack>
            </Box>
          )}
        </VStack>
      </Box>
    </Box>
  );
} 