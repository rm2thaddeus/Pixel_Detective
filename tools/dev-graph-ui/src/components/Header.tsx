'use client';

import { Box, Flex, Text, Badge, useColorModeValue, HStack, Icon } from '@chakra-ui/react';
import { FiGitBranch, FiDatabase, FiActivity } from 'react-icons/fi';

export function Header() {
  // Dark mode aware colors
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.300');

  return (
    <Box
      as="header"
      bg={bgColor}
      borderBottom="1px"
      borderColor={borderColor}
      px={6}
      py={4}
      position="sticky"
      top={0}
      zIndex={10}
      shadow="sm"
    >
      <Flex align="center" justify="space-between" maxW="7xl" mx="auto">
        <HStack spacing={4}>
          <HStack spacing={2}>
            <Icon as={FiGitBranch} boxSize={6} color="blue.500" />
            <Text fontSize="xl" fontWeight="bold" color={textColor}>
              Dev Graph
            </Text>
          </HStack>
          <Badge colorScheme="blue" variant="subtle">
            Standalone
          </Badge>
        </HStack>

        <HStack spacing={4}>
          <HStack spacing={2}>
            <Icon as={FiDatabase} boxSize={4} color="green.500" />
            <Text fontSize="sm" color={mutedTextColor}>
              Neo4j Connected
            </Text>
          </HStack>
          <HStack spacing={2}>
            <Icon as={FiActivity} boxSize={4} color="purple.500" />
            <Text fontSize="sm" color={mutedTextColor}>
              API Active
            </Text>
          </HStack>
        </HStack>
      </Flex>
    </Box>
  );
}
