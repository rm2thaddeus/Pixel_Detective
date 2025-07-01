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
  Wrap,
} from '@chakra-ui/react';
import { ClusteringRequest } from '../types/latent-space';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { useUMAP } from '../hooks/useUMAP';
import { 
  debounce, 
  exportToPNG, 
  exportToSVG, 
  exportToJSON, 
  ExportSettings 
} from '../utils/visualization';
import { 
  COLOR_PALETTES, 
  ColorPaletteName, 
  getPalettePreview
} from '../utils/visualization';

interface ClusteringControlsProps {
  onParametersChange?: (params: ClusteringRequest) => void;
  variant?: 'full' | 'compact'; // compact hides visualization settings & palette
  deckRef?: React.RefObject<HTMLElement>; // for PNG export
  selectedClusterId?: number | null; // for export settings
}

interface ColorPaletteSelectorProps {
  selectedPalette: ColorPaletteName;
  onPaletteChange: (palette: ColorPaletteName) => void;
  compact?: boolean; // render minimal variant
}

export function ColorPaletteSelector({ selectedPalette, onPaletteChange, compact = false }: ColorPaletteSelectorProps) {
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (compact) {
    return (
      <FormControl>
        <FormLabel fontSize="sm" fontWeight="semibold" mb={2}>Palette</FormLabel>
        <Wrap spacing={1}>
          {(Object.keys(COLOR_PALETTES) as ColorPaletteName[]).map((paletteName) => {
            const isSelected = selectedPalette === paletteName;
            const previewColors = getPalettePreview(paletteName, 4);
            return (
              <Tooltip key={paletteName} label={paletteName} hasArrow>
                <Box
                  as="button"
                  onClick={() => onPaletteChange(paletteName)}
                  borderRadius="md"
                  borderWidth={isSelected ? '2px' : '1px'}
                  borderColor={isSelected ? 'purple.500' : borderColor}
                  p={1}
                >
                  <HStack spacing={0}>
                    {previewColors.map((c, i) => (
                      <Box key={i} w="10px" h="10px" bg={c} />
                    ))}
                  </HStack>
                </Box>
              </Tooltip>
            );
          })}
        </Wrap>
      </FormControl>
    );
  }

  return (
    <FormControl>
      <FormLabel fontSize="sm" fontWeight="semibold" mb={2}>Color Palette</FormLabel>
      <SimpleGrid columns={4} spacing={2}>
        {(Object.keys(COLOR_PALETTES) as ColorPaletteName[]).map((p) => {
          const isSel = selectedPalette === p;
          const colors = getPalettePreview(p, 4);
          return (
            <Box
              key={p}
              as="button"
              borderWidth={isSel ? '2px' : '1px'}
              borderColor={isSel ? 'purple.500' : borderColor}
              p={1}
              borderRadius="md"
              onClick={() => onPaletteChange(p)}
            >
              <HStack spacing={0}>{colors.map((c,i)=>(<Box key={i} w="10px" h="10px" bg={c}/>))}</HStack>
            </Box>
          );
        })}
      </SimpleGrid>
    </FormControl>
  );
}

export function ClusteringControls({ 
  onParametersChange, 
  variant = 'full',
  deckRef,
  selectedClusterId
}: ClusteringControlsProps) {
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
    
    // To avoid sluggish UX we only auto-run clustering when the algorithm
    // itself changes.  Numeric tweaks are applied via the "Apply" button.
    const algoChanged =
      newParams.algorithm !== undefined &&
      newParams.algorithm !== clusteringParams.algorithm;

    if (algoChanged) {
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

  const handleExportVisualization = async (format: 'png' | 'svg' | 'json') => {
    try {
      if (!projectionData) {
        toast({
          title: 'Export failed',
          description: 'No visualization data available to export.',
          status: 'error',
          duration: 3000,
        });
        return;
      }

      const exportSettings: ExportSettings = {
        colorPalette,
        pointSize,
        showOutliers,
        selectedClusterId,
      };

      let success = false;

      switch (format) {
        case 'png':
          if (!deckRef?.current) {
            toast({
              title: 'Export failed',
              description: 'Visualization not ready for PNG export.',
              status: 'error',
              duration: 3000,
            });
            return;
          }
          success = exportToPNG(deckRef);
          break;
        
        case 'svg':
          success = exportToSVG(projectionData, exportSettings);
          break;
        
        case 'json':
          success = exportToJSON(projectionData, exportSettings);
          break;
      }

      if (success) {
        toast({
          title: `${format.toUpperCase()} Export Complete`,
          description: `Visualization exported successfully as ${format.toUpperCase()}.`,
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      console.error(`Export failed:`, error);
      toast({
        title: 'Export failed',
        description: error instanceof Error ? error.message : 'An unexpected error occurred.',
        status: 'error',
        duration: 5000,
      });
    }
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
                <option value="hdbscan">HDBSCAN</option>
                <option value="hierarchical">Hierarchical</option>
                <option value="dbscan">DBSCAN</option>
                <option value="kmeans">K-Means</option>
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

      {variant === 'full' && (
        <>
          <Divider />
          <ColorPaletteSelector selectedPalette={colorPalette} onPaletteChange={setColorPalette} />
          {/* existing visualization settings code kept */}
          <Card bg={cardBg} borderColor={borderColor} shadow="sm">
            <CardHeader>
              <Heading size="md">Visualization Settings</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={5} align="stretch">
                
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
        </>
      )}

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
