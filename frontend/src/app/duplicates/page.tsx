"use client";

import { useState, useRef } from "react";
import {
  Box,
  Button,
  Heading,
  VStack,
  HStack,
  Text,
  Checkbox,
  Spinner,
  Alert,
  AlertIcon,
  SimpleGrid,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  useDisclosure,
} from "@chakra-ui/react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Header } from "@/components/Header";
import { useStore } from "@/store/useStore";
import {
  startFindSimilar,
  getFindSimilarReport,
  archiveSelection,
  FindSimilarTask,
} from "@/lib/api";

export default function DuplicatesPage() {
  const { collection } = useStore();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { isOpen, onOpen, onClose } = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  const startMutation = useMutation({
    mutationFn: () => startFindSimilar(0.98, 10),
    onSuccess: (data) => {
      setTaskId(data.task_id);
    },
  });

  const { data: report, isLoading } = useQuery<FindSimilarTask | null>({
    queryKey: ["dup-report", taskId],
    queryFn: () =>
      taskId ? getFindSimilarReport(taskId) : Promise.resolve(null),
    enabled: !!taskId,
    refetchInterval: taskId ? 5000 : false,
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveSelection(Array.from(selected)),
    onSuccess: () => setSelected(new Set()),
  });

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <Box minH="100vh">
      <Header />
      <Box p={8}>
        <Heading mb={4}>Duplicate Management</Heading>
        {!collection && (
          <Alert status="warning" mb={4}>
            <AlertIcon />
            Please select a collection first.
          </Alert>
        )}
        <VStack align="start" spacing={4}>
          <Button
            colorScheme="blue"
            onClick={() => startMutation.mutate()}
            isLoading={startMutation.isLoading}
            isDisabled={!collection || !!taskId}
          >
            Start Analysis
          </Button>
          {isLoading && (
            <HStack>
              <Spinner size="sm" />
              <Text>Scanning collection...</Text>
            </HStack>
          )}
          {report && (
            <Box w="full">
              <Text mb={2}>Status: {report.status}</Text>
              <Text mb={4}>Progress: {report.progress.toFixed(2)}%</Text>
              {report.status === "completed" && (
                <VStack align="start" spacing={4}>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                    {report.results.map((group) => (
                      <Box
                        key={group.group_id}
                        borderWidth="1px"
                        p={3}
                        borderRadius="md"
                      >
                        <Text fontWeight="bold" mb={2}>
                          Group {group.group_id}
                        </Text>
                        {group.points.map((p: any) => (
                          <HStack key={p.id} justify="space-between">
                            <Checkbox
                              isChecked={selected.has(p.id)}
                              onChange={() => toggleSelect(p.id)}
                            />
                            <Text fontSize="sm" noOfLines={1}>
                              {p.payload?.filename || p.id}
                            </Text>
                          </HStack>
                        ))}
                      </Box>
                    ))}
                  </SimpleGrid>
                  <Button
                    colorScheme="red"
                    onClick={onOpen}
                    isDisabled={selected.size === 0}
                    isLoading={archiveMutation.isLoading}
                  >
                    Archive Selection
                  </Button>
                </VStack>
              )}
            </Box>
          )}
        </VStack>
      </Box>
      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Archive Selection
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to archive {selected.size} image(s)?
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={onClose} mr={3}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={() => archiveMutation.mutate()}
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
