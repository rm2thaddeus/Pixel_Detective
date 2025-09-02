'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Box, Spinner, Text, VStack } from '@chakra-ui/react';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dev-graph page
    router.push('/dev-graph');
  }, [router]);

  return (
    <Box 
      minH="100vh" 
      display="flex" 
      alignItems="center" 
      justifyContent="center"
      bg="gray.50"
    >
      <VStack spacing={4}>
        <Spinner size="xl" color="blue.500" />
        <Text fontSize="lg" color="gray.600">
          Loading Dev Graph...
        </Text>
      </VStack>
    </Box>
  );
}