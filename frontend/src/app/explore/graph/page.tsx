'use client';

import { Box, Heading, VStack, HStack, Switch, FormLabel, Text } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { useState } from 'react';
import { KnowledgeGraph } from '@/components/explore/KnowledgeGraph';

export default function GraphPage() {
  const [clustering, setClustering] = useState(true);
  const [focusMode, setFocusMode] = useState(true);

  return (
    <Box minH="100vh">
      <Header />
      <Box maxW="6xl" mx="auto" p={8}>
        <VStack align="start" spacing={4} w="full">
          <Heading size="lg">Knowledge Graph</Heading>
          <HStack>
            <HStack>
              <FormLabel m={0}>Clustering</FormLabel>
              <Switch isChecked={clustering} onChange={(e) => setClustering(e.target.checked)} />
            </HStack>
            <HStack>
              <FormLabel m={0}>Focus Mode</FormLabel>
              <Switch isChecked={focusMode} onChange={(e) => setFocusMode(e.target.checked)} />
            </HStack>
          </HStack>
          <Text color="gray.500">Interactive Sigma.js graph with optional community clustering and neighborhood focus.</Text>
          <KnowledgeGraph clustering={clustering} focusMode={focusMode} />
        </VStack>
      </Box>
    </Box>
  );
}

