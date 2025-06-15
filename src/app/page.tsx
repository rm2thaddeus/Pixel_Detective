'use client';

import { useState } from 'react';
import { Box, Flex, Center, Text } from '@chakra-ui/react';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { CollectionStats } from '@/components/CollectionStats';
import { CollectionModal } from '@/components/CollectionModal';
import { LogsPage } from '@/components/LogsPage';
import { useStore } from '@/store/useStore';
import { ClientOnly } from '@/components/ClientOnly';

export default function Home() {
  const { collection, setCollection } = useStore();
  const [isCollectionModalOpen, setCollectionModalOpen] = useState(false);
  const [isLogsModalOpen, setLogsModalOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const handleJobStarted = (jobId: string) => {
    setSelectedJobId(jobId);
    setLogsModalOpen(true);
  };

  return (
    <Box minH="100vh">
      <ClientOnly>
        <Header />
      </ClientOnly>

      <Flex>
        <ClientOnly>
          <Sidebar onOpenCollectionModal={() => setCollectionModalOpen(true)} />
        </ClientOnly>
        <Box flex="1" p={8}>
          {collection ? (
            <ClientOnly>
              <CollectionStats 
                collectionName={collection} 
                onViewLogs={handleJobStarted} 
              />
            </ClientOnly>
          ) : (
            <Center h="80vh">
              <Text>Select a collection or create a new one to get started.</Text>
            </Center>
          )}
        </Box>
      </Flex>

      <ClientOnly>
        <CollectionModal
          isOpen={isCollectionModalOpen}
          onClose={() => setCollectionModalOpen(false)}
        />
      </ClientOnly>

      {selectedJobId && (
        <LogsPage
          isOpen={isLogsModalOpen}
          onClose={() => setLogsModalOpen(false)}
          jobId={selectedJobId}
        />
      )}
    </Box>
  );
} 