'use client';

import React from 'react';
import {
  Box,
  SimpleGrid,
  Text,
  VStack,
  Icon,
  Spinner,
  Center,
} from '@chakra-ui/react';
import { FiSearch } from 'react-icons/fi';
import NextImage from 'next/image';
import type { SearchResult } from '@/hooks/useSearch';

interface SearchResultsGridProps {
  results: SearchResult[];
  isLoading: boolean;
  onImageClick: (result: SearchResult) => void;
}

export function SearchResultsGrid({ results, isLoading, onImageClick }: SearchResultsGridProps) {
  if (isLoading) {
    return (
      <Center py={12}>
        <VStack spacing={4}>
          <Spinner size="xl" color="blue.500" />
          <Text>Searching...</Text>
        </VStack>
      </Center>
    );
  }

  if (results.length === 0) {
    return (
      <Center py={12}>
        <VStack spacing={4} textAlign="center">
          <Icon as={FiSearch} boxSize={12} color="textSecondary" />
          <Text fontSize="lg" fontWeight="medium">No results found</Text>
          <Text color="textSecondary">Try different keywords or upload an image to find similar ones.</Text>
        </VStack>
      </Center>
    );
  }

  return (
    <SimpleGrid columns={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing={6}>
      {results.map((result) => (
        result.payload?.filename && (
          <Box
            key={result.id}
            onClick={() => onImageClick(result)}
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
            role="group"
          >
            <NextImage
              src={`/api/v1/images/${result.id}/thumbnail`}
              alt={result.payload.filename}
              width={300}
              height={300}
              style={{ objectFit: 'cover', width: '100%', height: '250px' }}
            />
            <Box p={3} bg="cardPreviewBg" _groupHover={{bg: 'blue.500', color: 'white'}}>
              <Text fontSize="sm" isTruncated>
                {result.payload.filename}
              </Text>
            </Box>
          </Box>
        )
      ))}
    </SimpleGrid>
  );
} 