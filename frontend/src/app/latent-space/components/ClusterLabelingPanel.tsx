'use client';

import React, { useState, useMemo } from 'react';
import {
  VStack,
  HStack,
  Text,
  Input,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Badge,
  IconButton,
  useToast,
  SimpleGrid,
  Box,
  useColorModeValue,
  Divider,
  InputGroup,
  InputRightElement,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { 
  generateClusterColors, 
  getClusterSummary, 
  ColorPaletteName,
  getEnhancedPaletteDescription,
  getTopKeywords,
} from '../utils/visualization';
import { UMAPPoint } from '../types/latent-space';

interface ClusterLabelingPanelProps {
  points: UMAPPoint[];
  selectedClusterId?: number | null;
  colorPalette?: ColorPaletteName;
}

export function ClusterLabelingPanel({ 
  points, 
  selectedClusterId,
  colorPalette = 'observable'
}: ClusterLabelingPanelProps) {
  const { clusterLabels, setClusterLabel, setSelectedCluster } = useLatentSpaceStore();
  const [editingCluster, setEditingCluster] = useState<number | null>(null);
  const [labelInput, setLabelInput] = useState('');
  const [showAll, setShowAll] = useState(false);
  const toast = useToast();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  // Get unique clusters from points
  const clusters = Array.from(
    new Set(
      points
        .filter(p => p.cluster_id !== null && p.cluster_id !== undefined && p.cluster_id !== -1)
        .map(p => p.cluster_id!)
    )
  ).sort((a, b) => a - b);

  const clusterColors = generateClusterColors(clusters.length, colorPalette);

  const keywordSuggestions = useMemo(()=>{
    const sugg: Record<number,string[]> = {};
    clusters.forEach(cid=>{
      const pts = points.filter(p=>p.cluster_id===cid);
      sugg[cid] = getTopKeywords(pts as any, 4);
    });
    return sugg;
  }, [points, clusters]);

  // Helper to pull caption-like text from a point payload
  const extractCaption = (pt: any): string | null => {
    if (pt.caption && typeof pt.caption === 'string') {
      return pt.caption;
    }
    if (pt.payload) {
      const p = pt.payload as Record<string, any>;
      if (typeof p.caption === 'string') return p.caption;
      if (typeof p.alt === 'string') return p.alt;
      if (Array.isArray(p.tags) && p.tags.length) return p.tags.join(' ');
      if (typeof p.subject === 'string') return p.subject;
      // Fallback: any first string field longer than 6 characters
      for (const key in p) {
        if (typeof p[key] === 'string' && p[key].length > 6) return p[key];
      }
    }
    return null;
  };

  const captionSamples = useMemo(()=>{
    const map: Record<number,string[]> = {};
    clusters.forEach(cid=>{
      const caps = points
        .filter(p=>p.cluster_id===cid)
        .map(pt=>extractCaption(pt))
        .filter(Boolean) as string[];
      map[cid] = Array.from(new Set(caps)).slice(0,4);
    });
    return map;
  }, [points, clusters]);

  // Inspect payload keys for debugging when no captions are found
  const payloadKeys = useMemo(()=>{
    const map: Record<number,string[]> = {};
    clusters.forEach(cid=>{
      const pt = points.find(p=>p.cluster_id===cid);
      if (pt && typeof (pt as any).payload === 'object') {
        map[cid] = Object.keys((pt as any).payload as Record<string, any>);
      } else {
        map[cid] = [];
      }
    });
    return map;
  }, [points, clusters]);

  const handleStartEditing = (clusterId: number) => {
    setEditingCluster(clusterId);
    setLabelInput(clusterLabels[clusterId] || `Cluster ${clusterId}`);
  };

  const handleSaveLabel = (clusterId: number) => {
    if (labelInput.trim()) {
      setClusterLabel(clusterId, labelInput.trim());
        toast({
        title: 'Label saved',
        description: `Cluster ${clusterId} labeled as "${labelInput.trim()}"`,
          status: 'success',
          duration: 2000,
        });
    }
    setEditingCluster(null);
    setLabelInput('');
  };

  const handleCancelEditing = () => {
    setEditingCluster(null);
    setLabelInput('');
  };

  const displayedClusters = showAll ? clusters : clusters.slice(0, 6);

  return (
    <Card bg={cardBg} borderColor={borderColor} shadow="sm">
      <CardHeader>
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="md">Cluster Labels</Heading>
            <Text fontSize="sm" color="gray.600">
              {clusters.length} clusters found
            </Text>
          </VStack>
          <Badge colorScheme="purple" variant="subtle">
            {getEnhancedPaletteDescription(colorPalette).name}
          </Badge>
        </HStack>
      </CardHeader>
      <CardBody>
        <VStack spacing={4} align="stretch">
          
          {clusters.length === 0 ? (
            <Box textAlign="center" py={8}>
              <Text color="gray.500" fontSize="sm">
                No clusters found. Run clustering analysis to see cluster labels.
              </Text>
            </Box>
          ) : (
            <>
              {/* Cluster List */}
              <VStack spacing={3} align="stretch">
                {displayedClusters.map((clusterId, index) => {
                  const summary = getClusterSummary(points, clusterId);
                  const isSelected = selectedClusterId === clusterId;
                  const isEditing = editingCluster === clusterId;
                  const color = clusterColors[index % clusterColors.length];
                  const label = clusterLabels[clusterId] || `Cluster ${clusterId}`;

                  return (
                    <Box
                      key={clusterId}
                      p={3}
                      borderRadius="lg"
                      border="2px solid"
                      borderColor={isSelected ? 'purple.500' : borderColor}
                      bg={isSelected ? 'purple.50' : 'transparent'}
                      transition="all 0.2s"
                      _hover={{
                        borderColor: 'purple.300',
                        bg: 'purple.25',
                      }}
                    >
                      <VStack spacing={3} align="stretch">
                        
                        {/* Cluster Header */}
                        <HStack justify="space-between">
                          <HStack spacing={3}>
                            <Box
                              w="16px"
                              h="16px"
                              borderRadius="full"
                              bg={`rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3] / 255})`}
                              border="2px solid"
                              borderColor="white"
                              boxShadow="sm"
                            />
                            <VStack spacing={0} align="start">
                              <Text fontWeight="semibold" fontSize="sm">
                                {label}
                              </Text>
                              <Text fontSize="xs" color="gray.500">
                                ID: {clusterId}
                              </Text>
                              {/* Stats inline */}
                              <HStack fontSize="xs" color="gray.500" spacing={2}>
                                <Text>Pts: {summary.size}</Text>
                                <Text>Dens: {summary.density.toFixed(1)}</Text>
                                <Text>Spr: {summary.spread.toFixed(2)}</Text>
                              </HStack>
                              {captionSamples[clusterId]?.length>0 ? (
                                <Text fontSize="sm" color="gray.500" isTruncated maxW="250px" noOfLines={1}>
                                  "{captionSamples[clusterId][0]}"
                                </Text>
                              ) : (
                                payloadKeys[clusterId]?.length > 0 && (
                                  <Text fontSize="8px" color="red.400" isTruncated maxW="200px">
                                    payload keys: {payloadKeys[clusterId].join(', ')}
                                  </Text>
                                )
                              )}
                            </VStack>
                          </HStack>
                          <HStack spacing={1}>
                            <Button
                              size="xs"
                              variant={isSelected ? "solid" : "outline"}
                              colorScheme="purple"
                              onClick={() => setSelectedCluster(isSelected ? null : clusterId)}
                            >
                              {isSelected ? "Selected" : "Select"}
                            </Button>
                            <Button
                              size="xs"
                              variant="outline"
                              onClick={() => handleStartEditing(clusterId)}
                              isDisabled={isEditing}
                            >
                              Edit
                            </Button>
                          </HStack>
                        </HStack>

                        {/* Edit Input */}
                        {isEditing && (
                          <VStack spacing={2} align="stretch">
                            <Divider />
                            <FormControl id={`cluster-label-${clusterId}`}>
                              <FormLabel srOnly htmlFor={`cluster-label-${clusterId}`}>Cluster Label</FormLabel>
                              <InputGroup size="sm">
                                <Input
                                  id={`cluster-label-${clusterId}`}
                                  name="clusterLabel"
                                  value={labelInput}
                                  onChange={(e) => setLabelInput(e.target.value)}
                                  placeholder="Enter cluster label..."
                                  onKeyPress={(e) => {
                                    if (e.key === 'Enter') {
                                      handleSaveLabel(clusterId);
                                    } else if (e.key === 'Escape') {
                                      handleCancelEditing();
                                    }
                                  }}
                                  autoFocus
                                  aria-label="Cluster label"
                                />
                                <InputRightElement>
                                  <HStack spacing={1}>
                                    <IconButton
                                      size="xs"
                                      icon={<Text fontSize="xs">✓</Text>}
                                      colorScheme="green"
                                      variant="ghost"
                                      onClick={() => handleSaveLabel(clusterId)}
                                      aria-label="Save label"
                                    />
                                    <IconButton
                                      size="xs"
                                      icon={<Text fontSize="xs">✕</Text>}
                                      colorScheme="red"
                                      variant="ghost"
                                      onClick={handleCancelEditing}
                                      aria-label="Cancel editing"
                                    />
                                  </HStack>
                                </InputRightElement>
                              </InputGroup>
                            </FormControl>
                            {/* suggestions */}
                            {keywordSuggestions[clusterId]?.length>0 && (
                              <HStack spacing={1} flexWrap="wrap">
                                {keywordSuggestions[clusterId].map(word=>(
                                  <Badge
                                    key={word}
                                    cursor="pointer"
                                    colorScheme="gray"
                                    onClick={()=>setLabelInput(word.charAt(0).toUpperCase()+word.slice(1))}
                                  >{word}</Badge>
                                ))}
                              </HStack>
                            )}
                            {/* caption samples */}
                            {captionSamples[clusterId]?.length>0 && (
                              <VStack align="start" spacing={1} pt={2}>
                                <Text fontSize="xs" fontWeight="semibold" color="gray.600">
                                  Sample descriptions:
                                </Text>
                                {captionSamples[clusterId].map((cap,idx)=>(
                                  <Text 
                                    key={idx} 
                                    fontSize="sm" 
                                    color="gray.600"
                                    cursor="pointer"
                                    _hover={{ color: "purple.600", bg: "purple.50" }}
                                    p={1}
                                    borderRadius="md"
                                    onClick={() => setLabelInput(cap)}
                                    title="Click to use as label"
                                  >
                                    "{cap}"
                                  </Text>
                                ))}
                              </VStack>
                            )}
                            <Text fontSize="xs" color="gray.500">
                              Press Enter to save, Escape to cancel
                            </Text>
                          </VStack>
                        )}
                      </VStack>
                    </Box>
                  );
                })}
              </VStack>

              {/* Show More/Less Toggle */}
              {clusters.length > 6 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setShowAll(!showAll)}
                  colorScheme="gray"
                >
                  {showAll ? `Show Less` : `Show All ${clusters.length} Clusters`}
                </Button>
              )}

              {/* Quick Actions */}
              <Divider />
              <VStack spacing={2} align="stretch">
                <Text fontSize="sm" fontWeight="semibold">Quick Actions</Text>
                <SimpleGrid columns={2} spacing={2}>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      // Auto-label clusters based on their characteristics
                      clusters.forEach((clusterId, index) => {
                        const words = keywordSuggestions[clusterId] || [];
                        let autoLabel = '';

                        if (words.length) {
                          // Use top 2 keywords for a short descriptive label
                          autoLabel = words.slice(0, 2).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                        } else {
                          // Try to harvest words from captions if available
                          const captions = captionSamples[clusterId] || [];
                          if (captions.length) {
                            const tokens = captions[0]
                              .toLowerCase()
                              .replace(/[^a-z0-9\s]/g,' ')
                              .split(/\s+/)
                              .filter(t=>t.length>2 && !/\d/.test(t));
                            autoLabel = tokens.slice(0,2).map(w=>w.charAt(0).toUpperCase()+w.slice(1)).join(' ');
                          }

                          const summary = getClusterSummary(points, clusterId);
                          if (summary.density > 2) {
                            autoLabel = `Dense Group ${index + 1}`;
                          } else if (summary.spread > 5) {
                            autoLabel = `Scattered Group ${index + 1}`;
                          } else if (summary.size > 50) {
                            autoLabel = `Large Group ${index + 1}`;
                          } else if (summary.size < 10) {
                            autoLabel = `Small Group ${index + 1}`;
                          } else {
                            autoLabel = `Group ${index + 1}`;
                          }
                        }

                        setClusterLabel(clusterId, autoLabel);
                      });
                      
                      toast({
                        title: 'Auto-labeling complete',
                        description: `${clusters.length} clusters have been automatically labeled.`,
                        status: 'success',
                        duration: 3000,
                      });
                    }}
                  >
                    Auto Label
                  </Button>
              <Button
                size="sm"
                    variant="outline"
                    colorScheme="red"
                    onClick={() => {
                      clusters.forEach(clusterId => {
                        setClusterLabel(clusterId, '');
                      });
                      toast({
                        title: 'Labels cleared',
                        description: 'All cluster labels have been removed.',
                        status: 'info',
                        duration: 2000,
                      });
                    }}
                  >
                    Clear All
              </Button>
                </SimpleGrid>
              </VStack>
            </>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
} 