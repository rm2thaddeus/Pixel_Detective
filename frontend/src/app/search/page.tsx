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
  InputRightElement,
  useColorModeValue
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

interface SearchResult {
  id: string;
  filename?: string;
  caption?: string;
  score: number;
  thumbnail_url?: string;
  payload?: Record<string, any>;
}

interface TextSearchResponse {
  total_approx: number;
  page: number;
  per_page: number;
  results: SearchResult[];
  query: string;
  embedding_model?: string;
}

export default function SearchPage() {
  const { collection } = useStore();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchInfo, setSearchInfo] = useState<{model?: string, total?: number}>({});

  // Dark mode aware colors
  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.300');
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const tipsBgColor = useColorModeValue('gray.50', 'gray.800');
  const inputBgColor = useColorModeValue('white', 'gray.700');
  const inputBorderColor = useColorModeValue('gray.200', 'gray.600');

  const handleSearch = async () => {
    if (!collection) {
      return;
    }

    if (!query.trim()) {
      return;
    }

    try {
      setLoading(true);
      const response = await api.post<TextSearchResponse>('/api/v1/search/text', {
        text: query.trim(),
        limit: 12,
        offset: 0
      });

      setResults(response.data.results);
      setSearchInfo({
        model: response.data.embedding_model,
        total: response.data.total_approx
      });
      setHasSearched(true);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
      setSearchInfo({});
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
    <Box bg={bgColor} minH="100vh">
      <Header />
      <Box p={8} maxW="6xl" mx="auto">
        <VStack spacing={6} align="stretch">
          {/* Search Header */}
          <Box textAlign="center">
            <Text fontSize="3xl" fontWeight="bold" mb={2} color={textColor}>
              AI-Powered Image Search
            </Text>
            {collection ? (
              <VStack spacing={2}>
                <Text color="blue.500" fontSize="lg">
                  Searching in: {collection}
                </Text>
                {searchInfo.model && (
                  <Text fontSize="sm" color={mutedTextColor}>
                    Powered by {searchInfo.model}
                  </Text>
                )}
              </VStack>
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
                bg={inputBgColor}
                borderColor={inputBorderColor}
                color={textColor}
                _placeholder={{ color: mutedTextColor }}
                _focus={{
                  borderColor: 'blue.500',
                  boxShadow: '0 0 0 1px blue.500'
                }}
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
              <Text mt={4} color={mutedTextColor}>
                Analyzing your query and searching through images...
              </Text>
            </Box>
          )}

          {/* Results */}
          {!loading && hasSearched && (
            <Box>
              <HStack justify="space-between" align="center" mb={4}>
                <Text fontSize="xl" fontWeight="semibold" color={textColor}>
                  Search Results
                </Text>
                <HStack spacing={3}>
                  <Badge colorScheme="blue" fontSize="sm">
                    {results.length} results
                  </Badge>
                  {searchInfo.total && searchInfo.total > results.length && (
                    <Badge colorScheme="gray" fontSize="sm">
                      ~{searchInfo.total} total
                    </Badge>
                  )}
                </HStack>
              </HStack>

              {results.length === 0 ? (
                <Box textAlign="center" py={8}>
                  <Text fontSize="lg" color={mutedTextColor}>
                    No results found for &quot;{query}&quot;
                  </Text>
                  <Text color={mutedTextColor} mt={2}>
                    Try different keywords or make sure your collection has images.
                  </Text>
                </Box>
              ) : (
                <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                  {results.map((result, index) => (
                    <Card key={result.id || index} overflow="hidden" shadow="md" bg={cardBgColor}>
                      <Box position="relative">
                        <Image
                          src={result.thumbnail_url || '/placeholder-image.png'}
                          alt={result.filename || `Result ${index + 1}`}
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
                          <Text fontWeight="semibold" fontSize="sm" noOfLines={1} color={textColor}>
                            {result.filename || `Image ${index + 1}`}
                          </Text>
                          {result.caption && (
                            <Text fontSize="xs" color={mutedTextColor} noOfLines={2}>
                              {result.caption}
                            </Text>
                          )}
                          <HStack justify="space-between" w="full">
                            <Text fontSize="xs" color={mutedTextColor}>
                              Match: {Math.round(result.score * 100)}%
                            </Text>
                            <Text fontSize="xs" color={mutedTextColor}>
                              ID: {result.id}
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
            <Box bg={tipsBgColor} p={6} borderRadius="md" border="1px" borderColor={inputBorderColor}>
              <Text fontWeight="semibold" mb={3} color={textColor}>
                💡 AI Search Tips:
              </Text>
              <VStack align="start" spacing={1} fontSize="sm" color={mutedTextColor}>
                <Text>• <strong>Be descriptive:</strong> &quot;red car in parking lot&quot;</Text>
                <Text>• <strong>Use emotions:</strong> &quot;happy people&quot;, &quot;peaceful landscape&quot;</Text>
                <Text>• <strong>Mention colors/objects:</strong> &quot;blue sky&quot;, &quot;wooden table&quot;</Text>
                <Text>• <strong>Be specific:</strong> &quot;dog running on beach&quot; vs just &quot;dog&quot;</Text>
                <Text>• <strong>Try actions:</strong> &quot;person jumping&quot;, &quot;cat sleeping&quot;</Text>
              </VStack>
            </Box>
          )}
        </VStack>
      </Box>
    </Box>
  );
} 