'use client';

import { Box, Flex, Text, Badge, useColorModeValue, HStack, Icon, Button } from '@chakra-ui/react';
import { FiZap, FiHome, FiSearch, FiFolder } from 'react-icons/fi';
import { useStore } from '@/store/useStore';
import { useEffect, useState } from 'react';
import { ping } from '@/lib/api';
import { ColorModeButton } from '@/components/ui/color-mode';
import { useRouter } from 'next/navigation';

export function Header() {
  const { collection } = useStore();
  const [healthStatus, setHealthStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const router = useRouter();

  // Dark mode aware colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.300');

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
    <Box bg={bgColor} shadow="sm" px={6} py={4} borderBottom="1px" borderColor={borderColor}>
      <Flex justify="space-between" align="center">
        <HStack spacing={2}>
          <Icon as={FiZap} color="blue.500" boxSize={5} />
          <Text fontSize="xl" fontWeight="bold" color={textColor}>
            Pixel Detective
          </Text>
        </HStack>
        
        <Flex align="center" gap={4}>
          <Flex align="center" gap={2}>
            <Text fontSize="sm" color={mutedTextColor}>Backend:</Text>
            <Badge 
              colorScheme={getStatusColor()} 
              data-testid={`status-${healthStatus}`}
            >
              {healthStatus}
            </Badge>
          </Flex>
          
          {collection && (
            <Flex align="center" gap={2}>
              <Text fontSize="sm" color={mutedTextColor}>Collection:</Text>
              <Badge colorScheme="blue">{collection}</Badge>
            </Flex>
          )}

          <ColorModeButton />
        </Flex>

        <HStack spacing={6}>
          <Button
            variant="ghost"
            leftIcon={<Icon as={FiHome} />}
            onClick={() => router.push('/')}
          >
            Home
          </Button>
          <Button
            variant="ghost"
            leftIcon={<Icon as={FiSearch} />}
            onClick={() => router.push('/search')}
          >
            Search
          </Button>

          <Button
            variant="ghost"
            leftIcon={<Icon as={FiFolder} />}
            onClick={() => router.push('/collections')}
          >
            Collections
          </Button>
        </HStack>
      </Flex>
    </Box>
  );
} 