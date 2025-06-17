'use client';

import React from 'react';
import {
  Box,
  Input,
  InputGroup,
  InputRightElement,
  IconButton,
  HStack,
  useColorModeValue,
  Spinner,
  Badge,
  Icon,
  AspectRatio,
  VStack,
  Text,
  useToast,
} from '@chakra-ui/react';
import { FiSearch, FiUpload, FiX, FiType, FiImage } from 'react-icons/fi';
import NextImage from 'next/image';

interface SearchInputProps {
  query: string;
  onQueryChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSearch: () => void;
  onImageSelect: (file: File) => void;
  onClearImage: () => void;
  isLoading: boolean;
  imagePreview: string | null;
  selectedImage: File | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
}

export function SearchInput({
  query,
  onQueryChange,
  onSearch,
  onImageSelect,
  onClearImage,
  isLoading,
  imagePreview,
  selectedImage,
  fileInputRef,
}: SearchInputProps) {
  const [isDragOver, setIsDragOver] = React.useState(false);
  const toast = useToast();
  
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
      onImageSelect(imageFile);
    } else {
      toast({ title: 'Invalid file', description: 'Please drop an image file', status: 'error', duration: 3000 });
    }
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') onSearch();
  };
  
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onImageSelect(file);
  };

  return (
    <VStack spacing={4} w="full">
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
            onChange={onQueryChange}
            onKeyPress={handleKeyPress}
            bg="cardBg"
            border="2px solid"
            borderColor={isDragOver ? 'blue.400' : 'border'}
            _hover={{ borderColor: 'gray.400' }}
            _focus={{ borderColor: 'blue.500', boxShadow: '0 0 0 1px blue.500' }}
            pr="120px"
            fontSize="md"
          />
          <InputRightElement width="auto" pr={2}>
            <HStack spacing={1}>
              {selectedImage && (
                <Badge colorScheme='green' variant="subtle">
                  <Icon as={FiImage} mr={1} />
                  Image
                </Badge>
              )}
               {query && !selectedImage &&(
                <Badge colorScheme='blue' variant="subtle">
                  <Icon as={FiType} mr={1} />
                  Text
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
                icon={isLoading ? <Spinner size="sm" /> : <FiSearch />}
                size="sm"
                colorScheme="blue"
                onClick={onSearch}
                isLoading={isLoading}
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

      {imagePreview && selectedImage && (
        <HStack spacing={4} w="full" p={4} bg="cardPreviewBg" borderRadius="md">
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
              Selected: {selectedImage.name}
            </Text>
          </VStack>
          <IconButton
            aria-label="Remove image"
            icon={<FiX />}
            size="sm"
            variant="ghost"
            onClick={onClearImage}
          />
        </HStack>
      )}
    </VStack>
  );
} 