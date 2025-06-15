'use client';

import { useState, useRef } from 'react';
import { useToast } from '@chakra-ui/react';
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
  total_approx?: number;
}

interface EmbedResponse {
  embedding: number[];
}

export function useSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [searchType, setSearchType] = useState<'text' | 'image' | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const handleImageSelection = (file: File) => {
    setSelectedImage(file);
    setSearchType('image');
    setQuery('');

    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);

    if (value.trim()) {
      setSearchType('text');
      clearImage();
    } else {
      setSearchType(null);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSearch = async () => {
    if (!query.trim() && !selectedImage) {
      toast({
        title: 'Search required',
        description: 'Please enter a query or select an image',
        status: 'warning',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setLoading(true);
    setResults([]);

    try {
      let searchResponse;
      if (searchType === 'image' && selectedImage) {
        const reader = new FileReader();
        reader.readAsDataURL(selectedImage);
        reader.onload = async (e) => {
            const base64Image = e.target?.result as string;
            
            const embedResponse = await mlApi.post<EmbedResponse>('/api/v1/embed', {
              image_base64: base64Image.split(',')[1],
              filename: selectedImage.name
            });

            searchResponse = await api.post<SearchResponse>('/api/v1/search', {
              embedding: embedResponse.data.embedding,
              limit: 20,
              offset: 0
            });
            setResults(searchResponse.data.results || []);
            setLoading(false);
        };
      } else {
        searchResponse = await api.post<SearchResponse>('/api/v1/search/text', {
          query: query.trim(),
          limit: 20,
          offset: 0
        });
        setResults(searchResponse.data.results || []);
        setLoading(false);
      }
    } catch (error) {
      console.error("Search failed:", error);
      toast({
        title: 'Search failed',
        description: 'An error occurred during the search.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
      setLoading(false);
    }
  };

  return {
    query,
    setQuery,
    results,
    loading,
    selectedImage,
    imagePreview,
    searchType,
    fileInputRef,
    handleImageSelection,
    handleTextChange,
    handleSearch,
    clearImage,
  };
} 