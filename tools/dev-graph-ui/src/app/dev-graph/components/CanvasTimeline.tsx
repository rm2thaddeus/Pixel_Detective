'use client';

import { Box, Text, HStack, useColorModeValue, VStack, Button, IconButton, Select } from '@chakra-ui/react';
import { useMemo, useState, useEffect, useRef, useCallback } from 'react';
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

interface CanvasTimelineProps {
  events: TimelineEvent[];
  onSelect?: (ev: TimelineEvent) => void;
  onRangeSelect?: (startId: string, endId: string) => void;
  onTimeScrub?: (timestamp: string) => void;
  height?: number;
}

export function CanvasTimeline({ 
  events, 
  onSelect, 
  onRangeSelect,
  onTimeScrub,
  height = 200
}: CanvasTimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedTimeRange, setSelectedTimeRange] = useState<[number, number]>([0, 100]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [hoveredEvent, setHoveredEvent] = useState<TimelineEvent | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragType, setDragType] = useState<'start' | 'end' | 'scrub' | null>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0, dpr: 1 });

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('black', 'white');
  const timelineBgColor = useColorModeValue('#f7fafc', '#2d3748');
  const timelineLineColor = useColorModeValue('#4a5568', '#a0aec0');

  // Bucket events by day for density visualization
  const bucketedEvents = useMemo(() => {
    if (events.length === 0) return [];
    
    const buckets = new Map<string, TimelineEvent[]>();
    
    events.forEach(event => {
      const date = new Date(event.timestamp);
      const dayKey = date.toISOString().split('T')[0]; // YYYY-MM-DD
      
      if (!buckets.has(dayKey)) {
        buckets.set(dayKey, []);
      }
      buckets.get(dayKey)!.push(event);
    });
    
    return Array.from(buckets.entries())
      .map(([day, events]) => ({
        day,
        events,
        count: events.length,
        timestamp: new Date(day).getTime()
      }))
      .sort((a, b) => a.timestamp - b.timestamp);
  }, [events]);

  // Track canvas size and device pixel ratio
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const updateSize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      setCanvasSize(prev => {
        if (
          prev.width !== rect.width ||
          prev.height !== rect.height ||
          prev.dpr !== dpr
        ) {
          return { width: rect.width, height: rect.height, dpr };
        }
        return prev;
      });
    };

    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(canvas);

    return () => resizeObserver.disconnect();
  }, []);

  // Draw timeline on canvas
  const drawTimeline = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || bucketedEvents.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const { width, height, dpr } = canvasSize;
    if (width === 0 || height === 0) return;

    const needResize = canvas.width !== width * dpr || canvas.height !== height * dpr;
    if (needResize) {
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    const padding = 20;
    const timelineHeight = height - padding * 2;
    const timelineWidth = width - padding * 2;
    const maxCount = Math.max(...bucketedEvents.map(b => b.count));

    // Draw timeline background
    ctx.fillStyle = timelineBgColor;
    ctx.fillRect(padding, padding, timelineWidth, timelineHeight);

    // Draw timeline line
    ctx.strokeStyle = timelineLineColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding + timelineHeight / 2);
    ctx.lineTo(padding + timelineWidth, padding + timelineHeight / 2);
    ctx.stroke();

    // Draw commit density bars
    bucketedEvents.forEach((bucket, index) => {
      const x = padding + (index / (bucketedEvents.length - 1)) * timelineWidth;
      const barHeight = (bucket.count / maxCount) * (timelineHeight * 0.8);
      const y = padding + timelineHeight / 2 - barHeight / 2;

      // Color based on commit count intensity
      const intensity = bucket.count / maxCount;
      const color = intensity > 0.7 ? '#e53e3e' : intensity > 0.4 ? '#dd6b20' : '#38a169';
      
      ctx.fillStyle = color;
      ctx.fillRect(x - 2, y, 4, barHeight);

      // Draw commit dots for individual events
      bucket.events.forEach((event, eventIndex) => {
        const dotY = y + (eventIndex / bucket.events.length) * barHeight;
        ctx.fillStyle = '#2b8a3e';
        ctx.beginPath();
        ctx.arc(x, dotY, 2, 0, 2 * Math.PI);
        ctx.fill();
      });
    });

    // Draw time range selection
    if (selectedTimeRange[0] !== selectedTimeRange[1]) {
      const startX = padding + (selectedTimeRange[0] / 100) * timelineWidth;
      const endX = padding + (selectedTimeRange[1] / 100) * timelineWidth;
      
      ctx.fillStyle = 'rgba(43, 138, 62, 0.2)';
      ctx.fillRect(startX, padding, endX - startX, timelineHeight);
      
      // Draw range handles
      ctx.fillStyle = '#2b8a3e';
      ctx.fillRect(startX - 3, padding, 6, timelineHeight);
      ctx.fillRect(endX - 3, padding, 6, timelineHeight);
    }

    // Draw current time indicator
    if (events.length > 0 && events[currentTimeIndex]) {
      const currentEvent = events[currentTimeIndex];
      const eventDate = new Date(currentEvent.timestamp);
      const timeProgress = events.findIndex(e => e.timestamp === currentEvent.timestamp) / (events.length - 1);
      const currentX = padding + timeProgress * timelineWidth;
      
      ctx.strokeStyle = '#e53e3e';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(currentX, padding);
      ctx.lineTo(currentX, padding + timelineHeight);
      ctx.stroke();
    }

    // Draw hover effect
    if (hoveredEvent) {
      const eventDate = new Date(hoveredEvent.timestamp);
      const timeProgress = events.findIndex(e => e.timestamp === hoveredEvent.timestamp) / (events.length - 1);
      const hoverX = padding + timeProgress * timelineWidth;
      
      ctx.strokeStyle = '#3182ce';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(hoverX, padding);
      ctx.lineTo(hoverX, padding + timelineHeight);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [bucketedEvents, selectedTimeRange, currentTimeIndex, hoveredEvent, events, timelineBgColor, timelineLineColor, canvasSize]);

  // Handle mouse events
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || events.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const padding = 20;
    const timelineWidth = rect.width - padding * 2;
    
    const progress = Math.max(0, Math.min(1, (x - padding) / timelineWidth));
    const eventIndex = Math.floor(progress * (events.length - 1));
    const event = events[eventIndex];
    
    if (event) {
      setHoveredEvent(event);
    }
  }, [events]);

  const handleMouseLeave = useCallback(() => {
    setHoveredEvent(null);
  }, []);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || events.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const padding = 20;
    const timelineWidth = rect.width - padding * 2;
    
    const progress = Math.max(0, Math.min(1, (x - padding) / timelineWidth));
    const eventIndex = Math.floor(progress * (events.length - 1));
    const event = events[eventIndex];
    
    if (event && onSelect) {
      onSelect(event);
      setCurrentTimeIndex(eventIndex);
    }
  }, [events, onSelect]);

  // Redraw when data changes
  useEffect(() => {
    drawTimeline();
  }, [drawTimeline]);

  // Auto-refresh effect
  useEffect(() => {
    if (!isPlaying) return;
    
    const interval = setInterval(() => {
      if (currentTimeIndex < events.length - 1) {
        const nextIndex = currentTimeIndex + 1;
        setCurrentTimeIndex(nextIndex);
        if (onTimeScrub && events[nextIndex]) {
          onTimeScrub(events[nextIndex].timestamp);
        }
      } else {
        setCurrentTimeIndex(0);
        if (onTimeScrub && events[0]) {
          onTimeScrub(events[0].timestamp);
        }
      }
    }, 1000);
    
    return () => clearInterval(interval);
  }, [isPlaying, currentTimeIndex, events, onTimeScrub]);

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

        {/* Canvas Timeline */}
        <Box>
          <canvas
            ref={canvasRef}
            style={{ 
              width: '100%', 
              height: `${height}px`,
              cursor: 'crosshair',
              border: `1px solid ${borderColor}`,
              borderRadius: '4px'
            }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
          />
        </Box>

        {/* Current Event Info */}
        {events.length > 0 && events[currentTimeIndex] && (
          <Box>
            <Text fontSize="sm" mb={2}>
              Current: {new Date(events[currentTimeIndex].timestamp).toLocaleString()}
            </Text>
            <Text fontSize="xs" color="gray.500">
              Event {currentTimeIndex + 1} of {events.length}: {events[currentTimeIndex].title}
            </Text>
          </Box>
        )}

        {/* Hover Info */}
        {hoveredEvent && (
          <Box p={2} bg="gray.100" borderRadius="md">
            <Text fontSize="sm" fontWeight="bold">{hoveredEvent.title}</Text>
            <Text fontSize="xs" color="gray.600">
              {new Date(hoveredEvent.timestamp).toLocaleString()} • {hoveredEvent.author}
            </Text>
            {hoveredEvent.files_changed && hoveredEvent.files_changed.length > 0 && (
              <Text fontSize="xs" color="gray.500">
                {hoveredEvent.files_changed.length} files changed
              </Text>
            )}
          </Box>
        )}

        {/* Bucket Summary */}
        <Box>
          <Text fontSize="sm" mb={2}>Commit Density Summary</Text>
          <HStack spacing={4} fontSize="xs">
            <Text>Total Events: {events.length}</Text>
            <Text>Days: {bucketedEvents.length}</Text>
            <Text>Peak: {Math.max(...bucketedEvents.map(b => b.count))} commits/day</Text>
          </HStack>
        </Box>

        {events.length === 0 && (
          <Box textAlign="center" py={8}>
            <Text color="gray.500">No timeline events available</Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}

export default CanvasTimeline;
