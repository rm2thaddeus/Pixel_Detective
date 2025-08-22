'use client';

import { Box, Text, VStack, HStack, Badge } from '@chakra-ui/react';

export type TimelineEvent = {
  id: string;
  title: string;
  timestamp: string; // ISO string
  author?: string;
  type?: string;
};

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  const sorted = [...(events || [])].sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <Text fontWeight="bold" mb={2}>Timeline</Text>
      <VStack align="stretch" spacing={2} maxH="280px" overflowY="auto">
        {sorted.map(ev => (
          <HStack key={ev.id} justify="space-between" align="start">
            <Box>
              <Text fontSize="sm" fontWeight="semibold">{ev.title}</Text>
              <Text fontSize="xs" color="gray.600">{ev.author || 'unknown'}</Text>
            </Box>
            <HStack>
              {ev.type && <Badge>{ev.type}</Badge>}
              <Text fontSize="xs" color="gray.500">{new Date(ev.timestamp).toLocaleString()}</Text>
            </HStack>
          </HStack>
        ))}
        {sorted.length === 0 && (
          <Text fontSize="sm" color="gray.600">No events</Text>
        )}
      </VStack>
    </Box>
  );
}

export default TimelineView;


