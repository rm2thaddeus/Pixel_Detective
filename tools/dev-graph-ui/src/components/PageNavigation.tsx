'use client';

import { Box, HStack, Link, Text, Icon, useColorModeValue } from '@chakra-ui/react';
import { FiZap, FiBarChart, FiLayers } from 'react-icons/fi';

interface PageNavigationProps {
  currentPage: 'complex' | 'enhanced' | 'simple';
}

export function PageNavigation({ currentPage }: PageNavigationProps) {
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const activeBg = useColorModeValue('blue.100', 'blue.900');
  const activeText = useColorModeValue('blue.700', 'blue.300');

  const pages = [
    {
      id: 'complex',
      name: 'Complex View',
      icon: FiZap,
      href: '/dev-graph/complex',
      color: 'blue'
    },
    {
      id: 'enhanced',
      name: 'Enhanced Dashboard',
      icon: FiBarChart,
      href: '/dev-graph/enhanced',
      color: 'green'
    },
    {
      id: 'simple',
      name: 'Simple Dashboard',
      icon: FiLayers,
      href: '/dev-graph/simple',
      color: 'purple'
    }
  ];

  return (
    <Box
      bg={bgColor}
      borderBottom="1px"
      borderColor={borderColor}
      px={6}
      py={3}
    >
      <HStack spacing={4} maxW="7xl" mx="auto">
        <Text fontSize="sm" fontWeight="medium" color="gray.600">
          Navigate to:
        </Text>
        {pages.map((page) => (
          <Link
            key={page.id}
            href={page.href}
            _hover={{ textDecoration: 'none' }}
          >
            <HStack
              spacing={2}
              px={3}
              py={2}
              borderRadius="md"
              bg={currentPage === page.id ? activeBg : 'transparent'}
              _hover={{ bg: currentPage === page.id ? activeBg : 'whiteAlpha.200' }}
            >
              <Icon
                as={page.icon}
                boxSize={4}
                color={currentPage === page.id ? activeText : `${page.color}.500`}
              />
              <Text
                fontSize="sm"
                fontWeight={currentPage === page.id ? 'semibold' : 'normal'}
                color={currentPage === page.id ? activeText : `${page.color}.600`}
              >
                {page.name}
              </Text>
            </HStack>
          </Link>
        ))}
      </HStack>
    </Box>
  );
}
