'use client';

import { Box, Text, HStack, VStack, Button, IconButton, useColorModeValue, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { useMemo, useState, useEffect, useRef } from 'react';
import { FiPlay, FiPause, FiSkipBack, FiSkipForward, FiZoomIn, FiZoomOut } from 'react-icons/fi';
import { useCommitsBuckets } from '../hooks/useWindowedSubgraph';

export interface CommitBucket {
  bucket: string;
  commit_count: number;
  file_changes: number;
  granularity: string;
}

export interface EnhancedTimelineViewProps {
  onTimeRangeSelect?: (fromTimestamp: string, toTimestamp: string) => void;
  onCommitSelect?: (timestamp: string) => void;
  height?: number;
}

export function EnhancedTimelineView({ 
  onTimeRangeSelect,
  onCommitSelect,
  height = 200
}: EnhancedTimelineViewProps) {
  const [selectedRange, setSelectedRange] = useState<[number, number]>([0, 100]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTimeIndex, setCurrentTimeIndex] = useState(0);
  const [granularity, setGranularity] = useState<'day' | 'week'>('day');
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showComplexity, setShowComplexity] = useState(true);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const textColor = useColorModeValue('black', 'white');
  const accentColor = useColorModeValue('blue.500', 'blue.300');
  const selectedColor = useColorModeValue('green.500', 'green.300');

  // Fetch commits buckets data
  const { data: bucketsData, isLoading, error } = useCommitsBuckets(granularity, undefined, undefined, 1000);
  
  const buckets = bucketsData?.buckets || [];
  const performance = bucketsData?.performance;

  // Calculate time range from buckets
  const timeRange = useMemo(() => {
    if (buckets.length === 0) return { start: null, end: null };
    
    const sortedBuckets = [...buckets].sort((a, b) => 
      new Date(a.bucket).getTime() - new Date(b.bucket).getTime()
    );
    
    return {
      start: sortedBuckets[0]?.bucket,
      end: sortedBuckets[sortedBuckets.length - 1]?.bucket
    };
  }, [buckets]);

  // Draw timeline on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || buckets.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Calculate dimensions
    const padding = 20;
    const chartWidth = rect.width - (padding * 2);
    const chartHeight = rect.height - (padding * 2);
    const maxCommits = Math.max(...buckets.map(b => b.commit_count));

    // Draw grid lines
    ctx.strokeStyle = borderColor;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding + (chartHeight / 5) * i;
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(padding + chartWidth, y);
      ctx.stroke();
    }

    // Build prefix sums for cumulative calculations
    const commitPrefix: number[] = [];
    const filePrefix: number[] = [];
    let commitSum = 0;
    let fileSum = 0;
    buckets.forEach((b, i) => {
      commitSum += b.commit_count;
      fileSum += b.file_changes;
      commitPrefix[i] = commitSum;
      filePrefix[i] = fileSum;
    });

    // Draw bars based on mode
    buckets.forEach((bucket, index) => {
      const x = padding + (chartWidth / buckets.length) * index;
      const barWidth = (chartWidth / buckets.length) * 0.8;
      let barHeight;
      if (showComplexity) {
        // Graph complexity visualization - simulate growing complexity over time
        const cumulativeCommits = commitPrefix[index];
        const cumulativeFiles = filePrefix[index];

        // Simulate graph complexity as a function of cumulative activity
        const complexity = Math.min(100, Math.sqrt(cumulativeCommits * 0.1 + cumulativeFiles * 0.05));
        barHeight = (complexity / 100) * chartHeight;

        // Color based on complexity level
        const intensity = complexity / 100;
        const color = intensity > 0.7 ? `rgba(168, 85, 247, ${0.4 + intensity * 0.6})` : // purple for high complexity
                     intensity > 0.4 ? `rgba(59, 130, 246, ${0.4 + intensity * 0.6})` : // blue for medium
                     `rgba(34, 197, 94, ${0.4 + intensity * 0.6})`; // green for low

        ctx.fillStyle = color;
        ctx.fillRect(x, padding + chartHeight - barHeight, barWidth, barHeight);

        // Draw complexity indicator dots
        const dotCount = Math.min(5, Math.floor(complexity / 20));
        for (let i = 0; i < dotCount; i++) {
          const dotY = padding + chartHeight - barHeight - 5 - (i * 3);
          ctx.fillStyle = '#9f7aea';
          ctx.beginPath();
          ctx.arc(x + barWidth / 2, dotY, 1.5, 0, 2 * Math.PI);
          ctx.fill();
        }
      } else {
        // Traditional commit count visualization
        barHeight = (bucket.commit_count / maxCommits) * chartHeight;

        // Color based on commit count
        const intensity = bucket.commit_count / maxCommits;
        const color = `rgba(59, 130, 246, ${0.3 + intensity * 0.7})`; // blue with varying opacity

        ctx.fillStyle = color;
        ctx.fillRect(x, padding + chartHeight - barHeight, barWidth, barHeight);
      }

      // Draw border
      ctx.strokeStyle = accentColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(x, padding + chartHeight - barHeight, barWidth, barHeight);
    });

    // Draw selection range
    if (selectedRange[0] !== selectedRange[1]) {
      const startX = padding + (chartWidth * selectedRange[0] / 100);
      const endX = padding + (chartWidth * selectedRange[1] / 100);
      const selectionWidth = endX - startX;
      
      ctx.fillStyle = `rgba(34, 197, 94, 0.2)`; // green with low opacity
      ctx.fillRect(startX, padding, selectionWidth, chartHeight);
      
      ctx.strokeStyle = selectedColor;
      ctx.lineWidth = 2;
      ctx.strokeRect(startX, padding, selectionWidth, chartHeight);
    }

    // Draw labels
    ctx.fillStyle = textColor;
    ctx.font = '12px system-ui';
    ctx.textAlign = 'center';
    
    // Y-axis labels (commit counts or complexity)
    for (let i = 0; i <= 5; i++) {
      const value = showComplexity ? 
        Math.round((100 / 5) * (5 - i)) : // complexity percentage
        Math.round((maxCommits / 5) * (5 - i)); // commit count
      const y = padding + (chartHeight / 5) * i + 4;
      ctx.fillText(value.toString() + (showComplexity ? '%' : ''), padding - 10, y);
    }

    // X-axis labels (dates) - show every 10th bucket to avoid crowding
    const labelInterval = Math.max(1, Math.floor(buckets.length / 10));
    buckets.forEach((bucket, index) => {
      if (index % labelInterval === 0) {
        const x = padding + (chartWidth / buckets.length) * index + (chartWidth / buckets.length) / 2;
        const date = new Date(bucket.bucket);
        const label = granularity === 'day' 
          ? `${date.getMonth() + 1}/${date.getDate()}`
          : `Week ${Math.ceil(date.getDate() / 7)}`;
        
        ctx.save();
        ctx.translate(x, padding + chartHeight + 15);
        ctx.rotate(-Math.PI / 4);
        ctx.fillText(label, 0, 0);
        ctx.restore();
      }
    });

  }, [buckets, selectedRange, granularity, showComplexity, borderColor, textColor, accentColor, selectedColor]);

  // Handle canvas click for time selection
  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || buckets.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const padding = 20;
    const chartWidth = rect.width - (padding * 2);
    
    const clickPercent = Math.max(0, Math.min(100, ((x - padding) / chartWidth) * 100));
    const bucketIndex = Math.floor((clickPercent / 100) * buckets.length);
    
    if (bucketIndex >= 0 && bucketIndex < buckets.length) {
      const bucket = buckets[bucketIndex];
      onCommitSelect?.(bucket.bucket);
    }
  };

  // Handle range selection
  const handleRangeChange = (values: [number, number]) => {
    setSelectedRange(values);
    
    if (buckets.length > 0) {
      const startIndex = Math.floor((values[0] / 100) * (buckets.length - 1));
      const endIndex = Math.floor((values[1] / 100) * (buckets.length - 1));
      
      const startBucket = buckets[startIndex];
      const endBucket = buckets[endIndex];
      
      if (startBucket && endBucket) {
        onTimeRangeSelect?.(startBucket.bucket, endBucket.bucket);
      }
    }
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const zoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.5, 5));
  };

  const zoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.5, 0.5));
  };

  if (isLoading) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" height={height}>
        <HStack justify="center" height="100%">
          <Spinner size="lg" />
          <Text>Loading timeline data...</Text>
        </HStack>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" height={height}>
        <Alert status="error">
          <AlertIcon />
          Failed to load timeline data: {error.message}
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={4} bg={bgColor} borderWidth={1} borderColor={borderColor} borderRadius="md" height={height}>
      <VStack spacing={4} align="stretch" height="100%">
        {/* Header */}
        <HStack justify="space-between" align="center">
          <Text fontSize="lg" fontWeight="bold">Graph Evolution Timeline</Text>
          <HStack spacing={2}>
            <Button
              size="sm"
              variant={showComplexity ? 'solid' : 'outline'}
              colorScheme="purple"
              onClick={() => setShowComplexity(!showComplexity)}
            >
              {showComplexity ? 'Complexity' : 'Commits'}
            </Button>
            <Button
              size="sm"
              variant={granularity === 'day' ? 'solid' : 'outline'}
              onClick={() => setGranularity('day')}
            >
              Day
            </Button>
            <Button
              size="sm"
              variant={granularity === 'week' ? 'solid' : 'outline'}
              onClick={() => setGranularity('week')}
            >
              Week
            </Button>
          </HStack>
        </HStack>

        {/* Performance Info */}
        {performance && (
          <Text fontSize="xs" color="green.600">
            Loaded {buckets.length} buckets in {performance.query_time_ms}ms
          </Text>
        )}

        {/* Timeline Canvas */}
        <Box flex={1} position="relative">
          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            style={{
              width: '100%',
              height: '100%',
              cursor: 'crosshair',
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'top left'
            }}
          />
        </Box>

        {/* Controls */}
        <HStack justify="space-between" align="center">
          <HStack spacing={2}>
            <IconButton
              aria-label="Play/Pause"
              icon={isPlaying ? <FiPause /> : <FiPlay />}
              size="sm"
              onClick={togglePlayback}
            />
            <IconButton
              aria-label="Zoom In"
              icon={<FiZoomIn />}
              size="sm"
              onClick={zoomIn}
            />
            <IconButton
              aria-label="Zoom Out"
              icon={<FiZoomOut />}
              size="sm"
              onClick={zoomOut}
            />
          </HStack>
          
          <Text fontSize="sm" color="gray.600">
            {buckets.length} time buckets | Zoom: {Math.round(zoomLevel * 100)}%
          </Text>
        </HStack>

        {/* Range Selection Info */}
        {selectedRange[0] !== selectedRange[1] && buckets.length > 0 && (
          <Box p={2} bg="green.50" borderRadius="md" borderWidth={1} borderColor="green.200">
            <Text fontSize="sm" color="green.800">
              Selected range: {Math.round(selectedRange[0])}% - {Math.round(selectedRange[1])}%
              {timeRange.start && timeRange.end && (
                <Text fontSize="xs" color="green.600">
                  {new Date(timeRange.start).toLocaleDateString()} - {new Date(timeRange.end).toLocaleDateString()}
                </Text>
              )}
            </Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
