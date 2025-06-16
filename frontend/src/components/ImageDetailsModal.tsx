'use client';

import React, { useState, useEffect } from 'react';
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
  HStack,
  Tag,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Image as CImage,
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
    tags?: string[];
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

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

const fetchImageDetails = async (imageId: string): Promise<ImageDetails> => {
    const response = await api.get(`/api/v1/images/${imageId}/info`);
    return response.data;
};

export function ImageDetailsModal({ imageId, isOpen, onClose }: ImageDetailsModalProps) {
    const [fullImageError, setFullImageError] = useState(false);
    const [clientDimensions, setClientDimensions] = useState<{w:number, h:number} | null>(null);
    const { data: imageDetails, isLoading, error } = useQuery<ImageDetails, Error>({
        queryKey: ['imageDetails', imageId],
        queryFn: () => fetchImageDetails(imageId!),
        enabled: !!imageId,
    });

    useEffect(() => {
        setFullImageError(false);
        setClientDimensions(null);
    }, [imageId]);

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
              {/* Caption & tags */}
              {imageDetails.caption && (
                <Text fontSize="2xl" fontWeight="bold" textAlign="center">
                  {imageDetails.caption}
                </Text>
              )}

              {imageDetails.tags && imageDetails.tags.length > 0 && (
                <HStack justifyContent="center" spacing={2} flexWrap="wrap">
                  {imageDetails.tags.map((tag) => (
                    <Tag key={tag} colorScheme="blue" variant="subtle">
                      {tag}
                    </Tag>
                  ))}
                </HStack>
              )}

              <Center>
                <AspectRatio ratio={(imageDetails.width && imageDetails.height) ? imageDetails.width / imageDetails.height : 1} w="full" maxW="800px">
                  {fullImageError ? (
                    <NextImage
                      src={`${API_URL}/api/v1/images/${imageDetails.id}/thumbnail`}
                      alt={imageDetails.filename}
                      width={imageDetails.width || 400}
                      height={imageDetails.height || 400}
                      onLoadingComplete={(img) => {
                        if ((!imageDetails.width || !imageDetails.height) && img?.naturalWidth && img?.naturalHeight) {
                          setClientDimensions({ w: img.naturalWidth, h: img.naturalHeight });
                        }
                      }}
                      style={{ objectFit: 'contain', borderRadius: 'var(--chakra-radii-md)' }}
                    />
                  ) : (
                    <CImage
                      src={`${API_URL}/api/v1/images/${imageDetails.id}/image`}
                      alt={imageDetails.filename}
                      maxH="80vh"
                      onError={() => setFullImageError(true)}
                      onLoad={({currentTarget}) => {
                        if ((!imageDetails.width || !imageDetails.height) && currentTarget.naturalWidth && currentTarget.naturalHeight) {
                          setClientDimensions({ w: currentTarget.naturalWidth, h: currentTarget.naturalHeight });
                        }
                      }}
                      objectFit="contain"
                      borderRadius="md"
                    />
                  )}
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
                        <Td>{(imageDetails.width || clientDimensions?.w || '?')} × {(imageDetails.height || clientDimensions?.h || '?')}</Td>
                      </Tr>
                      <Tr>
                        <Td fontWeight="medium">Format</Td>
                        <Td>{imageDetails.format !== 'unknown' ? imageDetails.format : (imageDetails.filename.split('.').pop()?.toUpperCase() || 'Unknown')}</Td>
                      </Tr>
                      {/* Additional metadata derived from EXIF if available */}
                      {imageDetails.exif && (
                        <>
                          {(() => {
                            const exif = imageDetails.exif || {};
                            const cameraMake = exif["Make"] || exif["Manufacturer"];
                            const cameraModel = exif["Model"];
                            const lensModel = exif["LensModel"] || exif["Lens"];
                            const dateTime = exif["DateTimeOriginal"] || exif["DateTime"];
                            const iso = exif["ISOSpeedRatings"] || exif["ISO"];
                            const exposure = exif["ExposureTime"];
                            const aperture = exif["FNumber"] || exif["ApertureValue"];
                            const focalLength = exif["FocalLength"];

                            return (
                              <>
                                {dateTime && (
                                  <Tr>
                                    <Td fontWeight="medium">Shot Date</Td>
                                    <Td>{dateTime}</Td>
                                  </Tr>
                                )}
                                {cameraMake || cameraModel ? (
                                  <Tr>
                                    <Td fontWeight="medium">Camera</Td>
                                    <Td>{[cameraMake, cameraModel].filter(Boolean).join(" ")}</Td>
                                  </Tr>
                                ) : null}
                                {lensModel && (
                                  <Tr>
                                    <Td fontWeight="medium">Lens</Td>
                                    <Td>{lensModel}</Td>
                                  </Tr>
                                )}
                                {exposure && (
                                  <Tr>
                                    <Td fontWeight="medium">Exposure</Td>
                                    <Td>{exposure}</Td>
                                  </Tr>
                                )}
                                {aperture && (
                                  <Tr>
                                    <Td fontWeight="medium">Aperture</Td>
                                    <Td>{aperture}</Td>
                                  </Tr>
                                )}
                                {iso && (
                                  <Tr>
                                    <Td fontWeight="medium">ISO</Td>
                                    <Td>{iso}</Td>
                                  </Tr>
                                )}
                                {focalLength && (
                                  <Tr>
                                    <Td fontWeight="medium">Focal Length</Td>
                                    <Td>{focalLength}</Td>
                                  </Tr>
                                )}
                              </>
                            );
                          })()}
                        </>
                      )}
                    </Tbody>
                  </Table>
                </TableContainer>

                {/* Advanced details accordion */}
                <Accordion allowToggle mt={4}>
                  <AccordionItem>
                    <AccordionButton>
                      <Text flex="1" textAlign="left" fontWeight="bold">Advanced</Text>
                      <AccordionIcon />
                    </AccordionButton>
                    <AccordionPanel pb={4}>
                      <TableContainer>
                        <Table size="sm">
                          <Tbody>
                            <Tr>
                              <Td fontWeight="medium">Image ID</Td>
                              <Td fontFamily="mono" fontSize="xs">{imageDetails.id}</Td>
                            </Tr>
                            <Tr>
                              <Td fontWeight="medium">File Hash</Td>
                              <Td fontFamily="mono" fontSize="xs">{imageDetails.file_hash}</Td>
                            </Tr>
                            <Tr>
                              <Td fontWeight="medium">File Path</Td>
                              <Td wordBreak="break-all">{imageDetails.full_path}</Td>
                            </Tr>
                            <Tr>
                              <Td fontWeight="medium">Color Mode</Td>
                              <Td>{imageDetails.mode}</Td>
                            </Tr>
                            <Tr>
                              <Td fontWeight="medium">Has Thumbnail</Td>
                              <Td>{imageDetails.has_thumbnail ? 'Yes' : 'No'}</Td>
                            </Tr>
                          </Tbody>
                        </Table>
                      </TableContainer>
                    </AccordionPanel>
                  </AccordionItem>
                </Accordion>
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
                window.open(`${API_URL}/api/v1/images/${imageDetails.id}/image`, '_blank');
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