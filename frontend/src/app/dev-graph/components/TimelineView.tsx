'use client';

import { Box, Text, VStack, HStack, Badge, RangeSlider, RangeSliderTrack, RangeSliderFilledTrack, RangeSliderThumb } from '@chakra-ui/react';

export type TimelineEvent = {
  id: string;
  title: string;
  timestamp: string; // ISO string
  author?: string;
  type?: string;
};

export function TimelineView({ events, onSelect, onRangeSelect }: { events: TimelineEvent[]; onSelect?: (ev: TimelineEvent) => void; onRangeSelect?: (startId: string, endId: string) => void }) {
  const sortedDesc = [...(events || [])].sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
  const sortedAsc = [...(events || [])].sort((a, b) => (a.timestamp < b.timestamp ? -1 : 1));
  const count = sortedAsc.length;
  const defaultRange: [number, number] = [0, Math.max(0, count - 1)];
  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <Text fontWeight="bold" mb={2}>Timeline</Text>
      {count > 1 && (
        <Box mb={3}>
          <RangeSlider aria-label={['start','end']} min={0} max={count - 1} defaultValue={defaultRange} onChangeEnd={(vals) => {
            const [startIdx, endIdx] = vals as [number, number];
            if (onRangeSelect) {
              const startId = sortedAsc[startIdx]?.id;
              const endId = sortedAsc[endIdx]?.id;
              if (startId && endId) onRangeSelect(startId, endId);
            }
          }}>
            <RangeSliderTrack>
              <RangeSliderFilledTrack />
            </RangeSliderTrack>
            <RangeSliderThumb index={0} />
            <RangeSliderThumb index={1} />
          </RangeSlider>
          <HStack justify="space-between">
            <Text fontSize="xs" color="gray.600">{new Date(sortedAsc[0].timestamp).toLocaleString()}</Text>
            <Text fontSize="xs" color="gray.600">{new Date(sortedAsc[count - 1].timestamp).toLocaleString()}</Text>
          </HStack>
        </Box>
      )}
      <VStack align="stretch" spacing={2} maxH="280px" overflowY="auto">
        {sortedDesc.map(ev => (
          <HStack key={ev.id} justify="space-between" align="start" cursor={onSelect ? 'pointer' : 'default'} onClick={() => onSelect && onSelect(ev)}>
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
        {sortedDesc.length === 0 && (
          <Text fontSize="sm" color="gray.600">No events</Text>
        )}
      </VStack>
    </Box>
  );
}

export default TimelineView;


