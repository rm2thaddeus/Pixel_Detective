'use client';

import { Box, Flex, Text, Badge } from '@chakra-ui/react';
import { useStore } from '@/store/useStore';
import { useEffect, useState } from 'react';
import { ping } from '@/lib/api';

export function Header() {
  const { collection } = useStore();
  const [healthStatus, setHealthStatus] = useState<'loading' | 'ok' | 'error'>('loading');

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await ping();
        setHealthStatus('ok');
      } catch {
        setHealthStatus('error');
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    switch (healthStatus) {
      case 'ok': return 'green';
      case 'error': return 'red';
      default: return 'gray';
    }
  };

  return (
    <Box bg="white" shadow="sm" px={6} py={4} borderBottom="1px" borderColor="gray.200">
      <Flex justify="space-between" align="center">
        <Text fontSize="xl" fontWeight="bold" color="gray.800">
          Vibe Coding - Image Search
        </Text>
        
        <Flex align="center" gap={4}>
          <Flex align="center" gap={2}>
            <Text fontSize="sm" color="gray.600">Backend:</Text>
            <Badge 
              colorScheme={getStatusColor()} 
              data-testid={`status-${healthStatus}`}
            >
              {healthStatus}
            </Badge>
          </Flex>
          
          {collection && (
            <Flex align="center" gap={2}>
              <Text fontSize="sm" color="gray.600">Collection:</Text>
              <Badge colorScheme="blue">{collection}</Badge>
            </Flex>
          )}
        </Flex>
      </Flex>
    </Box>
  );
} 