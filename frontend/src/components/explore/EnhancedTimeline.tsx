"use client";

import { Box, HStack, Text, VStack, Badge, useColorModeValue } from '@chakra-ui/react';
import React from 'react';
import type { EvolutionEvent } from '@/lib/api';

export function EnhancedTimeline({ events }: { events: EvolutionEvent[] }) {
  const lineColor = useColorModeValue('gray.300', 'gray.600');
  const dotColor = useColorModeValue('blue.500', 'blue.300');

  return (
    <Box w="full" overflowX="auto" py={4}>
      <HStack spacing={8} align="center">
        {events
          .slice()
          .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
          .map((e) => (
            <VStack key={e.id} spacing={2} minW="160px">
              <Badge>{new Date(e.timestamp).toLocaleDateString()}</Badge>
              <Box w="100%" h="2px" bg={lineColor} position="relative">
                <Box
                  position="absolute"
                  left="50%"
                  top="-6px"
                  transform="translateX(-50%)"
                  w="12px"
                  h="12px"
                  borderRadius="full"
                  bg={dotColor}
                />
              </Box>
              <Text fontWeight="semibold">{e.label}</Text>
              <Text fontSize="xs" color="gray.500">{e.type}</Text>
            </VStack>
          ))}
      </HStack>
    </Box>
  );
}
