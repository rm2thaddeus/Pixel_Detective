'use client';

import {
  VStack,
  HStack,
  Text,
  Badge,
  Card,
  CardBody,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Spinner,
  Alert,
  AlertIcon,
  Divider,
  Grid,
  GridItem,
  useColorModeValue,
} from '@chakra-ui/react';
import { useEffect, useState } from 'react';
import { useStore } from '@/store/useStore';
import { getCollectionInfo, CollectionInfo } from '@/lib/api';

export function CollectionStats() {
  const { collection } = useStore();
  const [collectionInfo, setCollectionInfo] = useState<CollectionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dark mode colors
  const cardBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.400');

  useEffect(() => {
    if (!collection) {
      setCollectionInfo(null);
      return;
    }

    const loadCollectionInfo = async () => {
      try {
        setLoading(true);
        setError(null);
        const info = await getCollectionInfo(collection);
        setCollectionInfo(info);
      } catch (err) {
        console.error('Failed to load collection info:', err);
        setError('Failed to load collection information');
      } finally {
        setLoading(false);
      }
    };

    loadCollectionInfo();
  }, [collection]);

  if (!collection) {
    return (
      <Card bg={cardBg} size="sm">
        <CardBody>
          <Alert status="info" size="sm">
            <AlertIcon />
            <Text fontSize="sm">No collection selected</Text>
          </Alert>
        </CardBody>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card bg={cardBg} size="sm">
        <CardBody>
          <HStack>
            <Spinner size="sm" />
            <Text fontSize="sm" color={mutedTextColor}>Loading collection info...</Text>
          </HStack>
        </CardBody>
      </Card>
    );
  }

  if (error || !collectionInfo) {
    return (
      <Card bg={cardBg} size="sm">
        <CardBody>
          <Alert status="error" size="sm">
            <AlertIcon />
            <Text fontSize="sm">{error || 'Failed to load collection info'}</Text>
          </Alert>
        </CardBody>
      </Card>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'green': return 'green';
      case 'yellow': return 'yellow';
      case 'red': return 'red';
      default: return 'gray';
    }
  };

  return (
    <VStack spacing={4} align="stretch">
      <Card bg={cardBg} size="sm">
        <CardBody>
          <VStack spacing={3} align="stretch">
            <HStack justify="space-between">
              <Text fontWeight="semibold" color={textColor}>{collectionInfo.name}</Text>
              <Badge colorScheme={getStatusColor(collectionInfo.status)} size="sm">
                {collectionInfo.status}
              </Badge>
            </HStack>
            
            {collectionInfo.is_active && (
              <Badge colorScheme="blue" size="sm" w="fit-content">
                Active Collection
              </Badge>
            )}
          </VStack>
        </CardBody>
      </Card>

      <Card bg={cardBg} size="sm">
        <CardBody>
          <Text fontSize="sm" fontWeight="semibold" mb={3} color={textColor}>
            Collection Statistics
          </Text>
          
          <Grid templateColumns="repeat(2, 1fr)" gap={4}>
            <GridItem>
              <Stat size="sm">
                <StatLabel color={mutedTextColor}>Images</StatLabel>
                <StatNumber color={textColor} fontSize="lg">
                  {collectionInfo.points_count.toLocaleString()}
                </StatNumber>
                <StatHelpText color={mutedTextColor}>Total images</StatHelpText>
              </Stat>
            </GridItem>
            
            <GridItem>
              <Stat size="sm">
                <StatLabel color={mutedTextColor}>Vectors</StatLabel>
                <StatNumber color={textColor} fontSize="lg">
                  {collectionInfo.vectors_count.toLocaleString()}
                </StatNumber>
                <StatHelpText color={mutedTextColor}>
                  {collectionInfo.indexed_vectors_count.toLocaleString()} indexed
                </StatHelpText>
              </Stat>
            </GridItem>
          </Grid>

          <Divider my={3} />

          <VStack spacing={2} align="stretch">
            <Text fontSize="xs" fontWeight="semibold" color={mutedTextColor}>
              Configuration
            </Text>
            <HStack justify="space-between">
              <Text fontSize="xs" color={mutedTextColor}>Vector Size:</Text>
              <Text fontSize="xs" color={textColor}>
                {collectionInfo.config.vector_size || 'Unknown'}
              </Text>
            </HStack>
            <HStack justify="space-between">
              <Text fontSize="xs" color={mutedTextColor}>Distance:</Text>
              <Text fontSize="xs" color={textColor}>
                {collectionInfo.config.distance || 'Unknown'}
              </Text>
            </HStack>
          </VStack>

          {collectionInfo.sample_points.length > 0 && (
            <>
              <Divider my={3} />
              <VStack spacing={2} align="stretch">
                <Text fontSize="xs" fontWeight="semibold" color={mutedTextColor}>
                  Recent Images ({collectionInfo.sample_points.length})
                </Text>
                {collectionInfo.sample_points.map((point) => (
                  <HStack key={point.id} justify="space-between" py={1}>
                    <Text fontSize="xs" color={textColor} noOfLines={1} flex="1">
                      {point.filename}
                    </Text>
                    <HStack spacing={1}>
                      {point.has_thumbnail && (
                        <Badge colorScheme="green" size="xs">T</Badge>
                      )}
                      {point.has_caption && (
                        <Badge colorScheme="blue" size="xs">C</Badge>
                      )}
                    </HStack>
                  </HStack>
                ))}
              </VStack>
            </>
          )}
        </CardBody>
      </Card>
    </VStack>
  );
} 