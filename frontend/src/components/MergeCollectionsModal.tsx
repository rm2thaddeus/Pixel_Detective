import { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Button,
  FormControl,
  FormLabel,
  Input,
  Checkbox,
  VStack,
  HStack,
  Spinner,
  useToast,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCollections, mergeCollections } from '@/lib/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function MergeCollectionsModal({ isOpen, onClose }: Props) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: getCollections,
  });

  const [destName, setDestName] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>([]);

  useEffect(() => {
    if (!isOpen) {
      setDestName('');
      setSelectedSources([]);
    }
  }, [isOpen]);

  const mutation = useMutation({
    mutationFn: () => mergeCollections(destName, selectedSources),
    onSuccess: () => {
      toast({
        title: 'Merge started',
        description: `Building '${destName}' from ${selectedSources.length} collections`,
        status: 'info',
      });
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      onClose();
    },
    onError: (err: any) => {
      toast({
        title: 'Merge failed',
        description: err.message ?? 'Unknown error',
        status: 'error',
      });
    },
  });

  const toggleSource = (name: string) => {
    setSelectedSources((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
  };

  const canSubmit = destName.trim().length > 0 && selectedSources.length >= 1;

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Merge Collections</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <FormControl>
              <FormLabel>Destination Collection Name</FormLabel>
              <Input
                placeholder="master_collection"
                value={destName}
                onChange={(e) => setDestName(e.target.value)}
              />
            </FormControl>

            {isLoading ? (
              <HStack justifyContent="center" py={4}>
                <Spinner />
              </HStack>
            ) : (
              <FormControl>
                <FormLabel>Select Source Collections</FormLabel>
                <VStack maxH="240px" overflowY="auto" align="start">
                  {collections?.map((name) => (
                    <Checkbox
                      key={name}
                      isChecked={selectedSources.includes(name)}
                      onChange={() => toggleSource(name)}
                    >
                      {name}
                    </Checkbox>
                  ))}
                </VStack>
              </FormControl>
            )}
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button colorScheme="blue" onClick={() => mutation.mutate()} isDisabled={!canSubmit} isLoading={mutation.isLoading}>
            Start Merge
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
} 