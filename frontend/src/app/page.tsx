'use client';
import { useEffect, useState } from 'react';
import { ping } from '../lib/api';
import { Button, Box, Text } from '@chakra-ui/react';

export default function Home() {
  const [status, setStatus] = useState<string>('unknown');

  async function handlePing() {
    const res = await ping();
    setStatus(res);
  }

  useEffect(() => {
    handlePing();
  }, []);

  return (
    <Box p={8} textAlign="center">
      <Text fontSize="xl" mb={4}>Backend status: {status}</Text>
      <Button colorScheme="teal" onClick={handlePing}>Refresh</Button>
    </Box>
  );
}
