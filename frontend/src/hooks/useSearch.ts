'use client';

import { useState, useRef } from 'react';
import { useToast } from '@chakra-ui/react';
import { useMutation } from '@tanstack/react-query';
import { api, mlApi } from '@/lib/api';

// Define more specific and consistent interfaces for our data
export interface SearchResultPayload {
  filename: string;
  [key: string]: any;
}

export interface SearchResult {
  id: string;
  payload: SearchResultPayload;
  score: number;
}

interface SearchResponse {
  results: SearchResult[];
}

interface TextSearchVariables {
  type: 'text';
  query: string;
  filters?: Record<string, any>; // Optional filters for hybrid search
}

interface ImageSearchVariables {
  type: 'image';
  file: File;
  filters?: Record<string, any>; // Optional filters for hybrid search
}

type SearchVariables = TextSearchVariables | ImageSearchVariables;

async function performSearch(variables: SearchVariables): Promise<SearchResponse> {
  if (variables.type === 'text') {
    const response = await api.post<SearchResponse>('/api/v1/search', {
      query: variables.query,
      limit: 20,
      offset: 0,
      filters: variables.filters, // Include filters if provided
    });
    return response.data;
  } else {
    // Use new backend endpoint that handles embedding + search in one step
    const form = new FormData();
    form.append('file', variables.file);
    
    // Add filters as query parameter for image search
    const params: Record<string, any> = { limit: 20, offset: 0 };
    if (variables.filters) {
      params.filters = JSON.stringify(variables.filters);
    }
    
    const response = await api.post<SearchResponse>('/api/v1/search/image', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params,
    });
    return response.data;
  }
}

export function useSearch() {
  const [query, setQuery] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, any> | undefined>(undefined);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const searchMutation = useMutation<SearchResponse, Error, SearchVariables>({
    mutationFn: performSearch,
    onError: (error) => {
      toast({
        title: 'Search failed',
        description: error.message || 'An unexpected error occurred.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    },
  });

  const handleImageSelection = (file: File) => {
    setSelectedImage(file);
    setQuery('');
    const reader = new FileReader();
    reader.onload = (e) => setImagePreview(e.target?.result as string);
    reader.readAsDataURL(file);
    searchMutation.mutate({ type: 'image', file, filters });
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };
  
  const handleTextSearch = () => {
    if (!query.trim()) {
      toast({
        title: 'Search query is empty',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    clearImage();
    searchMutation.mutate({ type: 'text', query: query.trim(), filters });
  }

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const updateFilters = (newFilters: Record<string, any> | undefined) => {
    setFilters(newFilters);
  };

  return {
    query,
    setQuery,
    results: searchMutation.data?.results || [],
    isLoading: searchMutation.isPending,
    error: searchMutation.error,
    selectedImage,
    imagePreview,
    fileInputRef,
    filters,
    handleImageSelection,
    handleTextChange,
    handleTextSearch,
    clearImage,
    updateFilters, // New function to update filters
  };
} 