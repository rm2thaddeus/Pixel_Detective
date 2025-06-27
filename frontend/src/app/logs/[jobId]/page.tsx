'use client';

import { useState, useRef } from 'react';
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
} from '@chakra-ui/react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getIngestStatus, archiveExact } from '@/lib/api';
import { Header } from '@/components/Header';

export default function JobLogsPage({ params }: { params: { jobId: string } }) {
  const { jobId } = params;
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

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
            <Box w="full">
              <Heading size="md" mt={6} mb={2}>
                Exact Duplicates Found
              </Heading>
              {data.exact_duplicates.length === 0 ? (
                <Text>No duplicates detected.</Text>
              ) : (
                <VStack align="start" spacing={2} w="full">
                  {data.exact_duplicates.map((dup) => (
                    <HStack key={dup.file_path} justify="space-between" w="full">
                      <Checkbox
                        isChecked={selected.has(dup.file_path)}
                        onChange={() => toggleSelect(dup.file_path)}
                      >
                        <Text fontSize="sm" noOfLines={1}>
                          {dup.file_path}
                        </Text>
                      </Checkbox>
                    </HStack>
                  ))}
                  <Button
                    colorScheme="red"
                    onClick={onOpen}
                    isDisabled={selected.size === 0}
                    isLoading={archiveMutation.isLoading}
                  >
                    Archive Selected
                  </Button>
                </VStack>
              )}
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
