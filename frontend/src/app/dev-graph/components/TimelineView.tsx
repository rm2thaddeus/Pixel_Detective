'use client';

import { Box, Text, HStack, RangeSlider, RangeSliderTrack, RangeSliderFilledTrack, RangeSliderThumb, useColorModeValue, VStack, Button, IconButton, Select } from '@chakra-ui/react';
import { useMemo, useState, useEffect } from 'react';
import { Chrono } from 'react-chrono';
import { FiPlay, FiPause, FiSkipBack, FiSkipForward } from 'react-icons/fi';

export type TimelineEvent = {
  id: string;
  title: string;
  timestamp: string; // ISO string
  author?: string;
  type?: string;
  commit_hash?: string;
  files_changed?: string[];
};

export function TimelineView({ 
  events, 
  onSelect, 
  onRangeSelect,
  onTimeScrub 
}: { 
  events: TimelineEvent[]; 
  onSelect?: (ev: TimelineEvent) => void; 
  onRangeSelect?: (startId: string, endId: string) => void;
  onTimeScrub?: (timestamp: string) => void;
}) {
  const [selectedTimeRange, setSelectedTimeRange] = useState<[number, number]>([0, 100]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(1000);
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const cardForeColor = useColorModeValue('black', 'white');

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !isPlaying) return;
    
    const interval = setInterval(() => {
      if (currentTimeIndex < events.length - 1) {
        const nextIndex = currentTimeIndex + 1;
        setCurrentTimeIndex(nextIndex);
        if (onTimeScrub && events[nextIndex]) {
          onTimeScrub(events[nextIndex].timestamp);
        }
      } else {
        // Loop back to start
        setCurrentTimeIndex(0);
        if (onTimeScrub && events[0]) {
          onTimeScrub(events[0].timestamp);
        }
      }
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [autoRefresh, isPlaying, currentTimeIndex, events, onTimeScrub, refreshInterval]);

  // Convert events to react-chrono format
  const chronoItems = useMemo(() => {
    return events.map((ev, index) => ({
      title: ev.title,
      cardTitle: ev.title,
      cardSubtitle: ev.author,
      cardDetailedText: ev.files_changed?.join(', ') || 'No files changed',
      date: new Date(ev.timestamp).toLocaleDateString(),
      timestamp: ev.timestamp,
      index,
    }));
  }, [events]);

  const handleRangeChange = (values: [number, number]) => {
    setSelectedTimeRange(values);
    if (onRangeSelect && events.length > 0) {
      const startIndex = Math.floor((values[0] / 100) * (events.length - 1));
      const endIndex = Math.floor((values[1] / 100) * (events.length - 1));
      onRangeSelect(events[startIndex].id, events[endIndex].id);
    }
  };

  const handleTimeScrub = (index: number) => {
    if (onTimeScrub && events[index]) {
      onTimeScrub(events[index].timestamp);
    }
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const skipToStart = () => {
    setCurrentTimeIndex(0);
    if (onTimeScrub && events[0]) {
      onTimeScrub(events[0].timestamp);
    }
  };

  const skipToEnd = () => {
    const lastIndex = events.length - 1;
    setCurrentTimeIndex(lastIndex);
    if (onTimeScrub && events[lastIndex]) {
      onTimeScrub(events[lastIndex].timestamp);
    }
  };

  const nextEvent = () => {
    if (currentTimeIndex < events.length - 1) {
      const nextIndex = currentTimeIndex + 1;
      setCurrentTimeIndex(nextIndex);
      if (onTimeScrub && events[nextIndex]) {
        onTimeScrub(events[nextIndex].timestamp);
      }
    }
  };

  const prevEvent = () => {
    if (currentTimeIndex > 0) {
      const prevIndex = currentTimeIndex - 1;
      setCurrentTimeIndex(prevIndex);
      if (onTimeScrub && events[prevIndex]) {
        onTimeScrub(events[prevIndex].timestamp);
      }
    }
  };

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md">
      <VStack spacing={4} align="stretch">
        {/* Timeline Controls */}
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="bold">Development Timeline</Text>
          <HStack spacing={2}>
            <IconButton
              aria-label="Skip to start"
              icon={<FiSkipBack />}
              size="sm"
              onClick={skipToStart}
              variant="ghost"
            />
            <IconButton
              aria-label="Previous event"
              icon={<FiSkipBack />}
              size="sm"
              onClick={prevEvent}
              variant="ghost"
            />
            <IconButton
              aria-label={isPlaying ? "Pause" : "Play"}
              icon={isPlaying ? <FiPause /> : <FiPlay />}
              size="sm"
              onClick={togglePlayback}
              variant="ghost"
            />
            <IconButton
              aria-label="Next event"
              icon={<FiSkipForward />}
              size="sm"
              onClick={nextEvent}
              variant="ghost"
            />
            <IconButton
              aria-label="Skip to end"
              icon={<FiSkipForward />}
              size="sm"
              onClick={skipToEnd}
              variant="ghost"
            />
          </HStack>
        </HStack>

        {/* Auto-refresh Controls */}
        <HStack spacing={4} align="center">
          <HStack spacing={2}>
            <Text fontSize="sm">Auto-refresh:</Text>
            <Button
              size="sm"
              variant={autoRefresh ? "solid" : "outline"}
              colorScheme={autoRefresh ? "green" : "gray"}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? "ON" : "OFF"}
            </Button>
          </HStack>
          
          {autoRefresh && (
            <HStack spacing={2}>
              <Text fontSize="sm">Interval:</Text>
              <Select
                size="sm"
                value={refreshInterval.toString()}
                onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                w="120px"
              >
                <option value="1000">1s</option>
                <option value="2000">2s</option>
                <option value="5000">5s</option>
                <option value="10000">10s</option>
              </Select>
            </HStack>
          )}
        </HStack>

        {/* Time Scrubber */}
        <Box>
          <Text fontSize="sm" mb={2}>Time Scrubber</Text>
          <RangeSlider
            value={selectedTimeRange}
            onChange={handleRangeChange}
            min={0}
            max={100}
            step={1}
            aria-label={['Start time', 'End time']}
          >
            <RangeSliderTrack>
              <RangeSliderFilledTrack />
            </RangeSliderTrack>
            <RangeSliderThumb index={0} />
            <RangeSliderThumb index={1} />
          </RangeSlider>
          <HStack justify="space-between" fontSize="xs" color="gray.500">
            <Text>{events.length > 0 ? new Date(events[0].timestamp).toLocaleDateString() : 'Start'}</Text>
            <Text>{events.length > 0 ? new Date(events[events.length - 1].timestamp).toLocaleDateString() : 'End'}</Text>
          </HStack>
        </Box>

        {/* Current Time Indicator */}
        {events.length > 0 && (
          <Box>
            <Text fontSize="sm" mb={2}>Current Time: {new Date(events[currentTimeIndex].timestamp).toLocaleString()}</Text>
            <Text fontSize="xs" color="gray.500">
              Event {currentTimeIndex + 1} of {events.length}: {events[currentTimeIndex].title}
            </Text>
          </Box>
        )}

        {/* Chrono Timeline */}
        {events.length > 0 && (
          <Box height="400px" overflow="hidden">
            <Chrono
              items={chronoItems}
              mode="VERTICAL"
              onItemSelected={(item) => {
                const index = chronoItems.findIndex(i => i.title === item.title);
                setCurrentTimeIndex(index);
                if (onSelect && events[index]) {
                  onSelect(events[index]);
                }
              }}
              theme={{
                primary: '#2b8a3e',
                secondary: '#e9ecef',
                cardBgColor: bgColor,
                                  cardForeColor: cardForeColor,
                titleColor: '#2b8a3e',
                titleColorActive: '#2b8a3e',
              }}
            />
          </Box>
        )}

        {events.length === 0 && (
          <Box textAlign="center" py={8}>
            <Text color="gray.500">No timeline events available</Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}

export default TimelineView;


