'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Image,
  Text,
  VStack,
  HStack,
  Badge,
  useColorModeValue,
  Portal,
} from '@chakra-ui/react';
import { UMAPPoint } from '../types/latent-space';

interface ThumbnailOverlayProps {
  point: UMAPPoint | null;
  mousePosition: { x: number; y: number } | null;
  onImageClick?: (point: UMAPPoint) => void;
}

export function ThumbnailOverlay({ 
  point, 
  mousePosition, 
  onImageClick 
}: ThumbnailOverlayProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const overlayBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  useEffect(() => {
    if (mousePosition) {
      // Position tooltip near mouse but avoid screen edges
      const offset = 15;
      setPosition({
        x: mousePosition.x + offset,
        y: mousePosition.y - offset,
      });
    }
  }, [mousePosition]);

  if (!point || !mousePosition) {
    return null;
  }

  return (
    <Portal>
      <Box
        position="fixed"
        left={`${position.x}px`}
        top={`${position.y}px`}
        zIndex={1000}
        bg={overlayBg}
        border="1px solid"
        borderColor={borderColor}
        borderRadius="md"
        p={3}
        boxShadow="lg"
        maxW="300px"
        onClick={() => onImageClick?.(point)}
        cursor={onImageClick ? 'pointer' : 'default'}
      >
        <VStack spacing={2} align="stretch">
          {point.thumbnail_base64 && (
            <Image
              src={`data:image/jpeg;base64,${point.thumbnail_base64}`}
              alt={point.filename || 'Image'}
              maxH="150px"
              objectFit="contain"
              borderRadius="sm"
            />
          )}
          
          <VStack spacing={1} align="stretch">
            {point.filename && (
              <Text fontSize="sm" fontWeight="medium" isTruncated>
                {point.filename}
              </Text>
            )}
            
            {point.caption && (
              <Text fontSize="xs" color="gray.600" noOfLines={2}>
                {point.caption}
              </Text>
            )}
            
            <HStack spacing={2} flexWrap="wrap">
              {point.cluster_id !== undefined && (
                <Badge colorScheme="blue" size="sm">
                  Cluster {point.cluster_id}
                </Badge>
              )}
              
              {point.is_outlier && (
                <Badge colorScheme="red" size="sm">
                  Outlier
                </Badge>
              )}
            </HStack>
            
            <HStack fontSize="xs" color="gray.500">
              <Text>x: {point.x.toFixed(2)}</Text>
              <Text>y: {point.y.toFixed(2)}</Text>
            </HStack>
          </VStack>
        </VStack>
      </Box>
    </Portal>
  );
} 