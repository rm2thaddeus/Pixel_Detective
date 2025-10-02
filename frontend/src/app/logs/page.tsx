'use client';
import { Box, Heading, Text } from '@chakra-ui/react';
import { Header } from '@/components/Header';

export default function LogsHome() {
  return (
    <Box minH="100vh">
      <Header />
      <Box p={8} maxW="3xl" mx="auto">
        <Heading size="lg" mb={4}>Activity Logs</Heading>
        <Text>Select an ingestion job to view details.</Text>
      </Box>
    </Box>
  );
}
