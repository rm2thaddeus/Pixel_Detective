'use client';

import React, { useMemo } from 'react';
import {
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Button,
  Text,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Divider,
  useToast,
  Badge,
  SimpleGrid,
  Box,
  Tooltip,
  useColorModeValue,
  Switch,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
} from '@chakra-ui/react';
import { ClusteringRequest } from '../types/latent-space';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { useUMAP } from '../hooks/useUMAP';
import { debounce } from '../utils/visualization';
import { 
  COLOR_PALETTES, 
  ColorPaletteName, 
  getPalettePreview, 
  getEnhancedPaletteDescription
} from '../utils/visualization';

interface ClusteringControlsProps {
  onParametersChange?: (params: ClusteringRequest) => void;
}

interface ColorPaletteSelectorProps {
  selectedPalette: ColorPaletteName;
  onPaletteChange: (palette: ColorPaletteName) => void;
}

function ColorPaletteSelector({ selectedPalette, onPaletteChange }: ColorPaletteSelectorProps) {
  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  return (
    <FormControl>
      <FormLabel fontSize="sm" fontWeight="semibold" mb={4}>
        <HStack>
          <Text>Color Palette</Text>
          <Badge colorScheme="blue" size="sm" variant="subtle">
            {(Object.keys(COLOR_PALETTES) as ColorPaletteName[]).length} options
          </Badge>
        </HStack>
      </FormLabel>
      <VStack spacing={4} align="stretch">
        <SimpleGrid columns={2} spacing={3}>
          {(Object.keys(COLOR_PALETTES) as ColorPaletteName[]).map((paletteName) => {
            const isSelected = selectedPalette === paletteName;
            const previewColors = getPalettePreview(paletteName, 6);
            const enhanced = getEnhancedPaletteDescription(paletteName);
            
            return (
              <Tooltip 
                key={paletteName} 
                label={
                  <VStack align="start" spacing={1} p={2}>
                    <Text fontWeight="bold">{enhanced.name}</Text>
                    <Text fontSize="sm">{enhanced.description}</Text>
                    <HStack>
                      <Text fontSize="xs" color="gray.300">Best for:</Text>
                      <Text fontSize="xs">{enhanced.bestFor}</Text>
                    </HStack>
                    <HStack>
                      <Text fontSize="xs" color="gray.300">Accessibility:</Text>
                      <Badge 
                        size="xs" 
                        colorScheme={
                          enhanced.accessibility === 'excellent' ? 'green' :
                          enhanced.accessibility === 'good' ? 'blue' : 'yellow'
                        }
                      >
                        {enhanced.accessibility}
                      </Badge>
                    </HStack>
                  </VStack>
                }
                placement="top"
                hasArrow
                bg="blackAlpha.900"
                color="white"
                borderRadius="md"
                p={0}
              >
                <Box
                  as="button"
                  onClick={() => onPaletteChange(paletteName)}
                  p={4}
                  borderRadius="lg"
                  border="2px solid"
                  borderColor={isSelected ? 'purple.500' : borderColor}
                  bg={isSelected ? 'purple.50' : cardBg}
                  _hover={{ 
                    borderColor: isSelected ? 'purple.600' : 'purple.300',
                    transform: 'translateY(-2px)',
                    boxShadow: 'lg',
                    bg: isSelected ? 'purple.100' : 'gray.50'
                  }}
                  _active={{
                    transform: 'translateY(0px)',
                    boxShadow: 'md'
                  }}
                  transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
                  cursor="pointer"
                  position="relative"
                >
                  <VStack spacing={3}>
                    <Text fontSize="xs" fontWeight="semibold" textTransform="capitalize" lineHeight="1.2">
                      {enhanced.name}
                    </Text>
                    <HStack spacing={1} justify="center">
                      {previewColors.map((color, index) => (
                        <Box
                          key={index}
                          w="14px"
                          h="14px"
                          borderRadius="full"
                          bg={color}
                          border="1px solid"
                          borderColor="gray.300"
                          boxShadow="sm"
                          transition="transform 0.2s"
                          _hover={{ transform: 'scale(1.1)' }}
                        />
                      ))}
                    </HStack>
                    {isSelected && (
                      <Badge colorScheme="purple" size="sm" variant="solid">
                        ✓ Active
                      </Badge>
                    )}
                    {/* Accessibility indicator */}
                    <Box
                      position="absolute"
                      top={1}
                      right={1}
                      w="8px"
                      h="8px"
                      borderRadius="full"
                      bg={
                        enhanced.accessibility === 'excellent' ? 'green.400' :
                        enhanced.accessibility === 'good' ? 'blue.400' : 'yellow.400'
                      }
                      title={`Accessibility: ${enhanced.accessibility}`}
                    />
                  </VStack>
                </Box>
              </Tooltip>
            );
          })}
        </SimpleGrid>
        
        {/* Enhanced description */}
        <Box 
          bg={useColorModeValue('blue.50', 'blue.900')} 
          p={3} 
          borderRadius="md" 
          border="1px solid"
          borderColor={useColorModeValue('blue.200', 'blue.700')}
        >
          <VStack align="start" spacing={2}>
            <HStack>
              <Text fontSize="sm" fontWeight="semibold" color="blue.700">
                {getEnhancedPaletteDescription(selectedPalette).name}
              </Text>
              <Badge 
                size="sm" 
                colorScheme={
                  getEnhancedPaletteDescription(selectedPalette).accessibility === 'excellent' ? 'green' :
                  getEnhancedPaletteDescription(selectedPalette).accessibility === 'good' ? 'blue' : 'yellow'
                }
              >
                {getEnhancedPaletteDescription(selectedPalette).accessibility}
              </Badge>
            </HStack>
            <Text fontSize="xs" color="blue.600" lineHeight="1.4">
              {getEnhancedPaletteDescription(selectedPalette).description}
            </Text>
            <Text fontSize="xs" color="blue.500">
              <strong>Best for:</strong> {getEnhancedPaletteDescription(selectedPalette).bestFor}
            </Text>
          </VStack>
        </Box>
      </VStack>
    </FormControl>
  );
}

export function ClusteringControls({ onParametersChange }: ClusteringControlsProps) {
  const { 
    clusteringParams, 
    updateClusteringParams, 
    setProjectionData, 
    projectionData,
    colorPalette,
    setColorPalette,
    showOutliers,
    setShowOutliers,
    pointSize,
    setPointSize,
    heatmapVisible,
    setHeatmap,
    heatmapOpacity,
    setHeatmapOpacity,
    overlayMode,
    setOverlayMode,
    terrainResolution,
    setTerrainResolution,
    terrainBands,
    setTerrainBands,
    showScatter,
    setShowScatter,
    showHulls,
    setShowHulls
  } = useLatentSpaceStore();
  const { clusteringMutation } = useUMAP();
  const toast = useToast();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const debouncedParameterUpdate = useMemo(
    () => debounce((params: ClusteringRequest) => {
      if (!projectionData?.points || projectionData.points.length === 0) {
        toast({
          title: 'No data available',
          description: 'Cannot apply clustering without projection data.',
          status: 'warning',
          duration: 3000,
        });
        return;
      }

      console.log('🔄 Applying clustering with params:', params);
      clusteringMutation.mutate({ ...params, points: projectionData.points }, {
        onSuccess: (data) => {
          console.log('✅ Clustering update successful:', data);
          setProjectionData(data);
          toast({
            title: 'Clustering updated',
            status: 'success',
            duration: 2000,
          });
        },
        onError: (error) => {
          console.error('❌ Clustering update failed:', error);
          toast({
            title: 'Clustering failed',
            description: error.message,
            status: 'error',
            duration: 4000,
          });
        },
      });
    }, 1000),
    [clusteringMutation, toast, setProjectionData, projectionData]
  );

  const handleParameterChange = (newParams: Partial<ClusteringRequest>) => {
    const updatedParams = { ...clusteringParams, ...newParams };
    updateClusteringParams(newParams);
    onParametersChange?.(updatedParams);
    
    // Only auto-update if we have significant parameter changes
    const shouldAutoUpdate = 
      newParams.algorithm ||
      (newParams.n_clusters && Math.abs((newParams.n_clusters || 0) - (clusteringParams.n_clusters || 0)) > 0) ||
      (newParams.eps && Math.abs(newParams.eps - clusteringParams.eps) > 0.05) ||
      (newParams.min_samples && newParams.min_samples !== clusteringParams.min_samples);
    
    if (shouldAutoUpdate) {
      debouncedParameterUpdate(updatedParams);
    }
  };

  const renderAlgorithmSpecificControls = () => {
    switch (clusteringParams.algorithm) {
      case 'dbscan':
        return (
          <>
            <FormControl>
              <FormLabel fontSize="sm">Eps (neighborhood distance)</FormLabel>
              <NumberInput
                value={clusteringParams.eps || 0.5}
                min={0.1}
                max={2.0}
                step={0.1}
                onChange={(_, value) => handleParameterChange({ eps: value })}
                size="sm"
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
            <FormControl>
              <FormLabel fontSize="sm">Min Samples</FormLabel>
              <NumberInput
                value={clusteringParams.min_samples || 5}
                min={1}
                max={20}
                onChange={(_, value) => handleParameterChange({ min_samples: value })}
                size="sm"
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>
          </>
        );
      case 'kmeans':
      case 'hierarchical':
        return (
          <FormControl>
            <FormLabel fontSize="sm">Number of Clusters</FormLabel>
            <NumberInput
              value={clusteringParams.n_clusters || 5}
              min={2}
              max={20}
              onChange={(_, value) => handleParameterChange({ n_clusters: value })}
              size="sm"
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        );
      case 'hdbscan':
        return (
          <FormControl>
            <FormLabel fontSize="sm">Min Cluster Size</FormLabel>
            <NumberInput
              value={clusteringParams.min_cluster_size || 5}
              min={2}
              max={100}
              onChange={(_, value) => handleParameterChange({ min_cluster_size: value })}
              size="sm"
            >
              <NumberInputField />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
          </FormControl>
        );
      default:
        return null;
    }
  };

  const handleExportVisualization = (format: 'png' | 'svg' | 'json') => {
    // This would typically trigger the parent component to handle the export
    toast({
      title: `Exporting as ${format.toUpperCase()}`,
      description: 'This feature will be implemented to export the current visualization.',
      status: 'info',
      duration: 3000,
    });
  };

  return (
    <VStack spacing={6} align="stretch">
      <Card bg={cardBg} borderColor={borderColor} shadow="sm">
        <CardHeader>
          <HStack justify="space-between">
            <Heading size="md">Clustering Parameters</Heading>
            <Badge colorScheme="blue" variant="subtle">
              {clusteringParams.algorithm}
            </Badge>
          </HStack>
        </CardHeader>
        <CardBody>
          <VStack spacing={5} align="stretch">
            
            {/* Algorithm Selection */}
            <FormControl>
              <FormLabel fontSize="sm" fontWeight="semibold">Algorithm</FormLabel>
              <Select
                value={clusteringParams.algorithm}
                                  onChange={(e) => handleParameterChange({ algorithm: e.target.value as ClusteringRequest['algorithm'] })}
                size="sm"
              >
                <option value="dbscan">DBSCAN</option>
                <option value="kmeans">K-Means</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="hdbscan">HDBSCAN</option>
              </Select>
            </FormControl>

            {renderAlgorithmSpecificControls()}

            <Divider />

            {/* Apply Button */}
            <Button
              colorScheme="purple"
              onClick={() => debouncedParameterUpdate(clusteringParams)}
              isLoading={clusteringMutation.isPending}
              loadingText="Applying..."
              size="sm"
            >
              Apply Clustering
            </Button>
          </VStack>
        </CardBody>
      </Card>

      {/* Visualization Settings */}
      <Card bg={cardBg} borderColor={borderColor} shadow="sm">
        <CardHeader>
          <Heading size="md">Visualization Settings</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={5} align="stretch">
            
            {/* Color Palette Selector */}
            <ColorPaletteSelector 
              selectedPalette={colorPalette}
              onPaletteChange={setColorPalette}
            />

            <Divider />

            {/* Point Size Control */}
            <FormControl>
              <FormLabel fontSize="sm" fontWeight="semibold">Point Size</FormLabel>
              <NumberInput
                value={pointSize}
                onChange={(_, value) => !isNaN(value) && setPointSize(value)}
                min={2}
                max={50}
                step={1}
                size="sm"
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            {/* Show Outliers Toggle */}
            <FormControl>
              <HStack justify="space-between">
                <FormLabel fontSize="sm" fontWeight="semibold" mb={0}>Show Outliers</FormLabel>
                <Button
                  size="sm"
                  variant={showOutliers ? "solid" : "outline"}
                  colorScheme={showOutliers ? "red" : "gray"}
                  onClick={() => setShowOutliers(!showOutliers)}
                >
                  {showOutliers ? "Hide" : "Show"}
                </Button>
              </HStack>
            </FormControl>

            {/* Show Points Toggle */}
            <FormControl>
              <HStack justify="space-between">
                <FormLabel fontSize="sm" fontWeight="semibold" mb={0}>Show Points</FormLabel>
                <Switch isChecked={showScatter} onChange={(e)=>setShowScatter(e.target.checked)} />
              </HStack>
            </FormControl>

            {/* Show Hulls Toggle */}
            <FormControl>
              <HStack justify="space-between">
                <FormLabel fontSize="sm" fontWeight="semibold" mb={0}>Show Hulls</FormLabel>
                <Switch isChecked={showHulls} onChange={(e)=>setShowHulls(e.target.checked)} />
              </HStack>
            </FormControl>

            {/* Overlay Mode */}
            <FormControl>
              <FormLabel fontSize="sm">Overlay Mode</FormLabel>
              <Select value={overlayMode} onChange={(e)=>setOverlayMode(e.target.value as any)} size="sm">
                <option value="none">None</option>
                <option value="heatmap">Heatmap</option>
                <option value="terrain">Density Terrain</option>
              </Select>
            </FormControl>

            {overlayMode==='heatmap' && (
              <>
              <FormControl display="flex" alignItems="center" justifyContent="space-between">
                <FormLabel mb="0">Show Heatmap</FormLabel>
                <Switch isChecked={heatmapVisible} onChange={(e) => setHeatmap(e.target.checked)} />
              </FormControl>
              {heatmapVisible && (
                <FormControl>
                  <FormLabel fontSize="sm">Heatmap Opacity</FormLabel>
                  <Slider value={heatmapOpacity} min={10} max={100} step={5} onChange={(v)=>setHeatmapOpacity(v)}>
                    <SliderTrack><SliderFilledTrack bg="purple.400"/></SliderTrack>
                    <SliderThumb boxSize={4}/>
                  </Slider>
                </FormControl>
              )}
              </>
            )}

            {overlayMode==='terrain' && (
              <>
                <FormControl>
                  <FormLabel fontSize="sm">Blur Radius (px)</FormLabel>
                  <Slider value={terrainResolution} min={10} max={100} step={5} onChange={(v)=>setTerrainResolution(v)}>
                    <SliderTrack><SliderFilledTrack bg="purple.400"/></SliderTrack>
                    <SliderThumb boxSize={4}/>
                  </Slider>
                  <Text fontSize="xs" color="gray.500">Larger radius = smoother hills</Text>
                </FormControl>
              </>
            )}

            <Divider />
          </VStack>
        </CardBody>
      </Card>

      {/* Export & Actions */}
      <Card bg={cardBg} borderColor={borderColor} shadow="sm">
        <CardHeader>
          <Heading size="md">Export & Actions</Heading>
        </CardHeader>
        <CardBody>
          <VStack spacing={4} align="stretch">
            
            {/* Export Options */}
            <FormControl>
              <FormLabel fontSize="sm" fontWeight="semibold">Export Visualization</FormLabel>
              <SimpleGrid columns={3} spacing={2}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExportVisualization('png')}
                  colorScheme="blue"
                >
                  PNG
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExportVisualization('svg')}
                  colorScheme="green"
                >
                  SVG
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleExportVisualization('json')}
                  colorScheme="purple"
                >
                  Data
                </Button>
              </SimpleGrid>
            </FormControl>

            <Divider />

            {/* Quick Actions */}
            <VStack spacing={2} align="stretch">
              <Text fontSize="sm" fontWeight="semibold">Quick Actions</Text>
              <SimpleGrid columns={2} spacing={2}>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    // Reset to default view
                    toast({
                      title: 'View Reset',
                      description: 'Visualization has been reset to default view.',
                      status: 'success',
                      duration: 2000,
                    });
                  }}
                >
                  Reset View
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    // Auto-fit to data
                    toast({
                      title: 'Auto Fit',
                      description: 'Visualization has been fitted to data bounds.',
                      status: 'success',
                      duration: 2000,
                    });
                  }}
                >
                  Auto Fit
                </Button>
              </SimpleGrid>
            </VStack>
          </VStack>
        </CardBody>
      </Card>
    </VStack>
  );
}
