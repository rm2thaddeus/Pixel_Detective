'use client';

import { useState, useRef, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Heading,
  Text,
  VStack,
  HStack,
  Spinner,
  Progress,
  Checkbox,
  Button,
  useDisclosure,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  Image,
  SimpleGrid,
  Card,
  CardBody,
  Flex,
  Code,
  useToast,
} from '@chakra-ui/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getIngestStatus, archiveExact, archiveAllDuplicates } from '@/lib/api';
import { Header } from '@/components/Header';

export default function JobLogsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  // Refs for auto-scroll behaviour
  const logsContainerRef = useRef<HTMLDivElement | null>(null);
  const errorsContainerRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();
  const toast = useToast();

  const { data, isLoading } = useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => getIngestStatus(jobId),
    refetchInterval: 3000,
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveExact(Array.from(selected)),
    onSuccess: () => setSelected(new Set()),
    onSettled: onClose,
  });

  // One-click archival of the *entire* duplicates list via new backend endpoint
  const archiveAllMutation = useMutation({
    mutationFn: () => archiveAllDuplicates(jobId),
    onSuccess: () => {
      // Duplicate list will shrink server-side → refetch status query
      setSelected(new Set());
      // react-query will auto-refetch because we call invalidateQueries below
      // but since we are inside the same component we can just rely on
      // automatic polling interval.
    },
  });

  const toggleSelect = (path: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const handleArchive = () => {
    archiveMutation.mutate();
  };

  // ------------------------------------------------------------------
  // Auto-scroll to bottom when logs or errors grow
  // ------------------------------------------------------------------
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTo({
        top: logsContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
    if (errorsContainerRef.current) {
      errorsContainerRef.current.scrollTo({
        top: errorsContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [data?.logs?.length, data?.errors?.length]);

  // 🔔 Redirect to home with toast once the job completes
  useEffect(() => {
    if (!isLoading && data?.status === 'completed') {
      toast({
        title: 'Ingestion Completed',
        description: `Job ${jobId} finished successfully.`,
        status: 'success',
        duration: 6000,
        isClosable: true,
      });
      router.push('/');
    }
  }, [data?.status, isLoading, jobId, router, toast]);

  return (
    <Box minH="100vh">
      <Header />
      <Box p={8} maxW="4xl" mx="auto">
        <Heading size="lg" mb={4}>
          Ingestion Job {jobId}
        </Heading>
        {isLoading || !data ? (
          <HStack mt={8}>
            <Spinner />
            <Text>Loading job status...</Text>
          </HStack>
        ) : (
          <VStack align="start" spacing={4} w="full">
            <Text>Status: {data.status}</Text>
            <Text>{data.message}</Text>
            <Progress value={data.progress} w="full" />

            {/* ------------------------------------------------------------------ */}
            {/* Streaming logs */}
            {/* ------------------------------------------------------------------ */}
            <Box w="full">
              <Heading size="md" mt={6} mb={2}>
                Job Logs
              </Heading>
              {data.logs.length === 0 ? (
                <Text>No runtime logs yet.</Text>
              ) : (
                <Box
                  ref={logsContainerRef}
                  maxH="400px"
                  overflowY="auto"
                  w="full"
                  p={2}
                  bg="gray.900"
                  borderRadius="md"
                >
                  <VStack align="start" spacing={1} fontSize="sm" color="gray.100">
                    {data.logs.map((line, idx) => (
                      <Code key={idx} w="full" whiteSpace="pre-wrap" bg="transparent" px={0}>
                        {typeof line === 'string'
                          ? line
                          : `${line.timestamp} [${line.level.toUpperCase()}] ${line.message}`}
                      </Code>
                    ))}
                  </VStack>
                </Box>
              )}
            </Box>

            {/* ------------------------------------------------------------------ */}
            {/* Error list (if any) */}
            {/* ------------------------------------------------------------------ */}
            {data.errors && data.errors.length > 0 && (
              <Box w="full">
                <Heading size="md" mt={6} mb={2} color="red.300">
                  Errors ({data.errors.length})
                </Heading>
                <Box
                  ref={errorsContainerRef}
                  maxH="300px"
                  overflowY="auto"
                  w="full"
                  p={2}
                  bg="red.900"
                  borderRadius="md"
                >
                  <VStack align="start" spacing={1} fontSize="sm" color="red.100">
                    {data.errors.map((line: string, idx: number) => (
                      <Code key={idx} w="full" whiteSpace="pre-wrap" bg="transparent" px={0}>
                        {line}
                      </Code>
                    ))}
                  </VStack>
                </Box>
              </Box>
            )}

            <Box w="full">
              <Heading size="md" mt={6} mb={2}>
                Exact Duplicates Found
              </Heading>
              {/* Always show control buttons; disable if no duplicates yet */}
              <VStack align="start" spacing={4} w="full">
                {data.exact_duplicates.length === 0 ? (
                  <Text>No duplicates detected yet – they will appear here as the ingest progresses.</Text>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} w="full">
                    {data.exact_duplicates.map((dup) => (
                      <Card key={dup.file_path} variant="outline">
                        <CardBody>
                          <HStack justify="space-between">
                            <VStack align="start">
                              <Text fontWeight="bold">New (Skipped)</Text>
                              <Text fontSize="sm" noOfLines={2} title={dup.file_path}>
                                {dup.file_path}
                              </Text>
                            </VStack>
                            <VStack align="start">
                              <Text fontWeight="bold">Original</Text>
                              {dup.existing_payload?.thumbnail_base64 ? (
                                <Image
                                  src={`data:image/jpeg;base64,${dup.existing_payload.thumbnail_base64}`}
                                  alt="Original image thumbnail"
                                  boxSize="100px"
                                  objectFit="cover"
                                  borderRadius="md"
                                />
                              ) : (
                                <Text fontSize="sm">No thumbnail</Text>
                              )}
                            </VStack>
                          </HStack>
                          <Flex mt={4}>
                            <Checkbox
                              isChecked={selected.has(dup.file_path)}
                              onChange={() => toggleSelect(dup.file_path)}
                            >
                              Archive New File
                            </Checkbox>
                          </Flex>
                        </CardBody>
                      </Card>
                    ))}
                  </SimpleGrid>
                )}
                {/* Action buttons (always rendered) */}
                <HStack spacing={4}>
                  <Button
                    colorScheme="red"
                    onClick={onOpen}
                    isDisabled={selected.size === 0 || data.exact_duplicates.length === 0}
                    isLoading={archiveMutation.isLoading}
                  >
                    Archive Selected Files
                  </Button>
                  <Button
                    variant="outline"
                    colorScheme="red"
                    onClick={() => archiveAllMutation.mutate()}
                    isDisabled={data.exact_duplicates.length === 0}
                    isLoading={archiveAllMutation.isLoading}
                  >
                    Archive ALL Duplicates
                  </Button>
                </HStack>
              </VStack>
            </Box>
          </VStack>
        )}
      </Box>

      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Archive Files
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to archive {selected.size} file(s)? This will
              move them to the _VibeDuplicates folder.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onClose} mr={3}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={handleArchive}
                isLoading={archiveMutation.isLoading}
              >
                Archive
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Box>
  );
}
