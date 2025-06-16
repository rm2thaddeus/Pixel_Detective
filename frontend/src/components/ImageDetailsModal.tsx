'use client';

import React from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  VStack,
  AspectRatio,
  Center,
  Divider,
  Text,
  TableContainer,
  Table,
  Tbody,
  Tr,
  Td,
  Spinner,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { FiDownload } from 'react-icons/fi';
import NextImage from 'next/image';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface ImageDetails {
    id: string;
    filename: string;
    full_path: string;
    caption?: string;
    file_hash: string;
    width: number;
    height: number;
    format: string;
    mode: string;
    has_thumbnail: boolean;
    exif?: Record<string, string>;
}

interface ImageDetailsModalProps {
  imageId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

const fetchImageDetails = async (imageId: string): Promise<ImageDetails> => {
    const response = await api.get(`/api/v1/images/${imageId}/info`);
    return response.data;
};

export function ImageDetailsModal({ imageId, isOpen, onClose }: ImageDetailsModalProps) {
    const { data: imageDetails, isLoading, error } = useQuery<ImageDetails, Error>({
        queryKey: ['imageDetails', imageId],
        queryFn: () => fetchImageDetails(imageId!),
        enabled: !!imageId,
    });

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Image Details</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {isLoading && <Center><Spinner /></Center>}
          {error && <Alert status="error"><AlertIcon />{error.message}</Alert>}
          {imageDetails && (
            <VStack spacing={6} align="stretch">
              <Center>
                <AspectRatio ratio={imageDetails.width / imageDetails.height || 1} w="full" maxW="500px">
                  <NextImage
                    src={`/api/v1/images/${imageDetails.id}/image`}
                    alt={imageDetails.filename}
                    width={imageDetails.width}
                    height={imageDetails.height}
                    style={{ objectFit: 'contain', borderRadius: 'var(--chakra-radii-md)' }}
                  />
                </AspectRatio>
              </Center>
              <Divider />
              <VStack align="stretch" spacing={4}>
                <Text fontSize="lg" fontWeight="bold">Information</Text>
                <TableContainer>
                  <Table size="sm">
                    <Tbody>
                      <Tr>
                        <Td fontWeight="medium">Filename</Td>
                        <Td>{imageDetails.filename}</Td>
                      </Tr>
                      <Tr>
                        <Td fontWeight="medium">Dimensions</Td>
                        <Td>{imageDetails.width} × {imageDetails.height}</Td>
                      </Tr>
                      <Tr>
                        <Td fontWeight="medium">Format</Td>
                        <Td>{imageDetails.format}</Td>
                      </Tr>
                      <Tr>
                        <Td fontWeight="medium">File Hash</Td>
                        <Td fontFamily="mono" fontSize="xs">{imageDetails.file_hash}</Td>
                      </Tr>
                    </Tbody>
                  </Table>
                </TableContainer>
              </VStack>
              {imageDetails.exif && Object.keys(imageDetails.exif).length > 0 && (
                <>
                  <Divider />
                  <VStack align="stretch" spacing={4}>
                    <Text fontSize="lg" fontWeight="bold">EXIF Data</Text>
                    <TableContainer>
                      <Table size="sm">
                        <Tbody>
                          {Object.entries(imageDetails.exif).map(([key, value]) => (
                            <Tr key={key}>
                              <Td fontWeight="medium">{key}</Td>
                              <Td>{String(value)}</Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </TableContainer>
                  </VStack>
                </>
              )}
            </VStack>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            leftIcon={<FiDownload />}
            colorScheme="blue"
            isDisabled={!imageDetails}
            onClick={() => {
              if (imageDetails) {
                window.open(`/api/v1/images/${imageDetails.id}/image`, '_blank');
              }
            }}
          >
            Download
          </Button>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 