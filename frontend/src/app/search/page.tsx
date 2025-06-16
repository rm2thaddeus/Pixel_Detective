'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  VStack,
  Text,
  useColorModeValue,
  useDisclosure,
  Card,
  CardBody,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { ClientOnly } from '@/components/ClientOnly';
import { useSearch, type SearchResult } from '@/hooks/useSearch';
import { SearchInput } from '@/components/SearchInput';
import { SearchResultsGrid } from '@/components/SearchResultsGrid';
import { ImageDetailsModal } from '@/components/ImageDetailsModal';
import { api } from '@/lib/api';
import { useStore } from '@/store/useStore';

export default function SearchPage() {
  const {
    query,
    results,
    isLoading,
    imagePreview,
    selectedImage,
    fileInputRef,
    handleTextChange,
    handleTextSearch,
    handleImageSelection,
    clearImage,
  } = useSearch();

  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const activeCollection = useStore((state) => state.collection);

  const handleImageClick = (result: SearchResult) => {
    setSelectedImageId(result.id);
    onOpen();
  };

  return (
    <Box minH="100vh" bg="pageBg">
      <ClientOnly>
        <Header />
      </ClientOnly>
      
      <Box maxW="6xl" mx="auto" p={6}>
        <VStack spacing={8} align="stretch">
          <VStack spacing={4} textAlign="center">
            <Text fontSize="3xl" fontWeight="bold">
              Search Your Images
            </Text>
            <Text fontSize="lg" color="textSecondary">
              Search by typing a description or drag & drop an image to find similar ones
            </Text>
          </VStack>

          <Card bg="cardBg">
            <CardBody>
                <SearchInput
                    query={query}
                    onQueryChange={handleTextChange}
                    onSearch={handleTextSearch}
                    onImageSelect={handleImageSelection}
                    onClearImage={clearImage}
                    isLoading={isLoading}
                    imagePreview={imagePreview}
                    selectedImage={selectedImage}
                    fileInputRef={fileInputRef}
                />
                {activeCollection && (
                  <Alert status="info" borderRadius="md" mt={4}>
                    <AlertIcon />
                    <Text fontSize="sm">Searching in collection: <strong>{activeCollection}</strong></Text>
                  </Alert>
                )}
            </CardBody>
          </Card>

          <SearchResultsGrid
            isLoading={isLoading}
            results={results}
            onImageClick={handleImageClick}
          />
        </VStack>
      </Box>

      <ImageDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        imageId={selectedImageId}
      />
    </Box>
  );
}