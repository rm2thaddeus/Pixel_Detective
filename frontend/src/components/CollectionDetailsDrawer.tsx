import {
  Drawer,
  DrawerOverlay,
  DrawerContent,
  DrawerHeader,
  DrawerBody,
  DrawerCloseButton,
  Text,
  VStack,
  HStack,
  Badge,
  Spinner,
  Button,
  Icon,
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiSearch, FiZap, FiFolder } from 'react-icons/fi';
import { useQuery } from '@tanstack/react-query';
import { getCollectionInfo, CollectionInfo } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  collectionName: string | null;
}

export function CollectionDetailsDrawer({ isOpen, onClose, collectionName }: Props) {
  const router = useRouter();
  const { data, isLoading, error } = useQuery<CollectionInfo | null, Error>(
    {
      queryKey: ['collectionInfo', collectionName],
      queryFn: () => collectionName ? getCollectionInfo(collectionName) : Promise.resolve(null),
      enabled: Boolean(collectionName && isOpen),
    }
  );

  const headerBg = useColorModeValue('gray.50', 'gray.900');

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="sm">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader bg={headerBg}>{collectionName || 'Collection'}</DrawerHeader>
        <DrawerBody>
          {isLoading && (
            <HStack justifyContent="center" py={8}>
              <Spinner />
            </HStack>
          )}
          {error && <Text color="red.500">Failed to load collection info.</Text>}
          {data && (
            <VStack align="stretch" spacing={4}>
              <HStack>
                <Badge colorScheme={data.is_active ? 'green' : 'gray'}>
                  {data.is_active ? 'Active' : 'Inactive'}
                </Badge>
                <Badge>{data.status}</Badge>
              </HStack>
              <Text>Points: {data.points_count}</Text>
              <Text>Vectors: {data.vectors_count}</Text>
              <Text>Vector Size: {data.config.vector_size}</Text>

              {/* Navigation Buttons */}
              <VStack pt={6} spacing={3} align="stretch">
                <Button
                  leftIcon={<Icon as={FiSearch} />}
                  onClick={() => {
                    router.push(`/search?collection=${collectionName}`);
                    onClose();
                  }}
                >
                  Open in Search
                </Button>
                <Button
                  leftIcon={<Icon as={FiZap} />}
                  onClick={() => {
                    router.push(`/latent-space?collection=${collectionName}`);
                    onClose();
                  }}
                >
                  Open in Latent Space
                </Button>
                <Button
                  variant="outline"
                  leftIcon={<Icon as={FiFolder} />}
                  onClick={() => {
                    router.push(`/collections?created=${collectionName}`);
                    onClose();
                  }}
                >
                  View Collections Grid
                </Button>
              </VStack>

              {/* Sample thumbnails could be added here later */}
            </VStack>
          )}
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
} 