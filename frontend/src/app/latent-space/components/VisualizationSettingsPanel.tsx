import React from 'react';
import {
  VStack,
  Card,
  CardBody,
  CardHeader,
  Heading,
  Divider,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  HStack,
  Text,
  Switch,
  Select,
  useColorModeValue,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { ColorPaletteSelector } from './ClusteringControls';

export const VisualizationSettingsPanel: React.FC = () => {
  const {
    pointSize,
    setPointSize,
    showOutliers,
    setShowOutliers,
    showScatter,
    setShowScatter,
    showHulls,
    setShowHulls,
    overlayMode,
    setOverlayMode,
    heatmapOpacity,
    setHeatmapOpacity,
    colorPalette,
    setColorPalette,
  } = useLatentSpaceStore();

  const cardBg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  return (
    <Card bg={cardBg} borderColor={borderColor} shadow="sm">
      <CardHeader pb={2}>
        <Heading as="h4" size="sm">Visualization Settings</Heading>
      </CardHeader>
      <CardBody>
        <VStack spacing={5} align="stretch">
          {/* Color Palette */}
          <ColorPaletteSelector selectedPalette={colorPalette} onPaletteChange={setColorPalette} compact />

          <Divider />

          {/* Point Size */}
          <VStack align="stretch" spacing={2}>
            <Text fontSize="sm" fontWeight="semibold">Point Size</Text>
            <Slider min={4} max={20} step={1} value={pointSize} onChange={setPointSize}>
              <SliderTrack><SliderFilledTrack /></SliderTrack>
              <SliderThumb boxSize={4}>{pointSize}</SliderThumb>
            </Slider>
          </VStack>

          {/* Toggles */}
          <HStack justify="space-between">
            <Text fontSize="sm">Show Outliers</Text>
            <Switch isChecked={showOutliers} onChange={(e) => setShowOutliers(e.target.checked)} />
          </HStack>
          <HStack justify="space-between">
            <Text fontSize="sm">Show Points</Text>
            <Switch isChecked={showScatter} onChange={(e) => setShowScatter(e.target.checked)} />
          </HStack>
          <HStack justify="space-between">
            <Text fontSize="sm">Show Hulls</Text>
            <Switch isChecked={showHulls} onChange={(e) => setShowHulls(e.target.checked)} />
          </HStack>

          <Divider />

          {/* Overlay Mode */}
          <VStack align="stretch" spacing={2}>
            <Text fontSize="sm" fontWeight="semibold">Overlay Mode</Text>
            <Select value={overlayMode} onChange={(e) => setOverlayMode(e.target.value as any)} size="sm">
              <option value="none">None</option>
              <option value="heatmap">Density</option>
              <option value="terrain">Terrain</option>
            </Select>
            {overlayMode === 'terrain' && (
              <VStack align="stretch" spacing={1} fontSize="xs">
                <Text>Blur Radius (px)</Text>
                <Slider min={10} max={100} step={1} value={heatmapOpacity} onChange={setHeatmapOpacity}>
                  <SliderTrack><SliderFilledTrack /></SliderTrack>
                  <SliderThumb boxSize={3}>{heatmapOpacity}</SliderThumb>
                </Slider>
                <Text color="gray.500">Larger radius = smoother hills</Text>
              </VStack>
            )}
          </VStack>
        </VStack>
      </CardBody>
    </Card>
  );
}; 