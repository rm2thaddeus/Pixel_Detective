'use client';

import { Box, Heading, Text, VStack, SimpleGrid, Button, useColorModeValue, Icon, Badge } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { Link as ChakraLink } from '@chakra-ui/react';
import { FaProjectDiagram, FaGlobeAmericas } from 'react-icons/fa';

export default function TimelineLandingPage() {
  const bg = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const textColor = useColorModeValue('gray.700', 'gray.200');

  return (
    <Box minH="100vh" bg={bg}>
      <Header />
      <Box maxW="6xl" mx="auto" px={8} py={12}>
        <VStack align="stretch" spacing={10}>
          <VStack align="start" spacing={3}>
            <Badge colorScheme="purple" borderRadius="full" px={3} py={1}>Developer Graph</Badge>
            <Heading size="lg">Choose Your Timeline Renderer</Heading>
            <Text color={textColor} maxW="3xl">
              We now provide dedicated experiences for both the classic SVG renderer and the new WebGL2 engine.
              Pick the mode that fits your hardware and exploration style.
            </Text>
          </VStack>

          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
            <Box bg={cardBg} borderRadius="lg" borderWidth="1px" borderColor={borderColor} p={6} shadow="md">
              <VStack align="start" spacing={4}>
                <Icon as={FaProjectDiagram} boxSize={8} color="purple.400" />
                <Heading size="md">SVG Timeline</Heading>
                <Text color={textColor}>
                  Optimized for universal compatibility and quick insights. Ideal for browsers without GPU acceleration
                  or when you prefer crisp vector rendering.
                </Text>
                <Button as={ChakraLink} href="/dev-graph/timeline/svg" colorScheme="purple" size="sm">
                  Open SVG Timeline
                </Button>
              </VStack>
            </Box>

            <Box bg={cardBg} borderRadius="lg" borderWidth="1px" borderColor={borderColor} p={6} shadow="md">
              <VStack align="start" spacing={4}>
                <Icon as={FaGlobeAmericas} boxSize={8} color="teal.400" />
                <Heading size="md">WebGL2 Timeline</Heading>
                <Text color={textColor}>
                  Harness GPU acceleration for dense histories, smooth camera work, and interactive filtering at scale.
                  Requires WebGL2 capable hardware for the best experience.
                </Text>
                <Button as={ChakraLink} href="/dev-graph/timeline/webgl" colorScheme="teal" size="sm">
                  Open WebGL2 Timeline
                </Button>
              </VStack>
            </Box>
          </SimpleGrid>
        </VStack>
      </Box>
    </Box>
  );
}
