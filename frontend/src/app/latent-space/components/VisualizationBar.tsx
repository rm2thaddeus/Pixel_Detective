import React from 'react';
import {
  HStack,
  Wrap,
  WrapItem,
  Box,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Tag,
  Tooltip,
  Select,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { useLatentSpaceStore } from '../hooks/useLatentSpaceStore';
import { COLOR_PALETTES, ColorPaletteName, getPalettePreview } from '../utils/visualization';

export const VisualizationBar: React.FC = () => {
  const {
    // palette
    colorPalette,
    setColorPalette,
    // point size
    pointSize,
    setPointSize,
    // toggles
    showOutliers,
    setShowOutliers,
    showScatter,
    setShowScatter,
    showHulls,
    setShowHulls,
    showVoronoi,
    setShowVoronoi,
    // overlay
    overlayMode,
    setOverlayMode,
    heatmapOpacity,
    setHeatmapOpacity,
    heatmapVisible,
    setHeatmap,
  } = useLatentSpaceStore();

  const borderColor = useColorModeValue('gray.200', 'gray.600');

  return (
    <HStack
      spacing={6}
      align="center"
      w="full"
      px={2}
      py={1}
      borderRadius="md"
      bg="gray.50"
      _dark={{ bg: 'gray.700' }}
      overflowX="auto"
    >
      {/* Palette Swatches */}
      <Wrap spacing={1} align="center">
        {(Object.keys(COLOR_PALETTES) as ColorPaletteName[]).map((paletteName) => {
          const isSelected = colorPalette === paletteName;
          const previewColors = getPalettePreview(paletteName, 4);
          return (
            <WrapItem key={paletteName}>
              <Tooltip label={paletteName} hasArrow>
                <Box
                  as="button"
                  borderRadius="md"
                  borderWidth={isSelected ? '2px' : '1px'}
                  borderColor={isSelected ? 'purple.500' : borderColor}
                  p={1}
                  onClick={() => setColorPalette(paletteName)}
                >
                  <HStack spacing={0}>
                    {previewColors.map((c, i) => (
                      <Box key={i} w="10px" h="10px" bg={c} />
                    ))}
                  </HStack>
                </Box>
              </Tooltip>
            </WrapItem>
          );
        })}
      </Wrap>

      {/* Point Size */}
      <HStack spacing={2} minW="140px" align="center">
        <Text fontSize="xs" whiteSpace="nowrap">Size</Text>
        <Slider
          aria-label="Point size"
          min={4}
          max={20}
          step={1}
          value={pointSize}
          onChange={setPointSize}
          w="100px"
        >
          <SliderTrack><SliderFilledTrack /></SliderTrack>
          <SliderThumb boxSize={3} />
        </Slider>
      </HStack>

      {/* Layer Toggles */}
      <Wrap spacing={2}>
        <WrapItem>
          <Tooltip label="Toggle scatter layer" hasArrow>
            <Tag
              size="sm"
              variant={showScatter ? 'solid' : 'subtle'}
              colorScheme="purple"
              cursor="pointer"
              onClick={() => setShowScatter(!showScatter)}
            >
              Points
            </Tag>
          </Tooltip>
        </WrapItem>
        <WrapItem>
          <Tooltip label="Toggle outliers" hasArrow>
            <Tag
              size="sm"
              variant={showOutliers ? 'solid' : 'subtle'}
              colorScheme="red"
              cursor="pointer"
              onClick={() => setShowOutliers(!showOutliers)}
            >
              Outliers
            </Tag>
          </Tooltip>
        </WrapItem>
        <WrapItem>
          <Tooltip label="Toggle hull polygons" hasArrow>
            <Tag
              size="sm"
              variant={showHulls ? 'solid' : 'subtle'}
              colorScheme="cyan"
              cursor="pointer"
              onClick={() => setShowHulls(!showHulls)}
            >
              Hulls
            </Tag>
          </Tooltip>
        </WrapItem>
      </Wrap>

      {/* Overlay Mode Chips */}
      <Wrap spacing={2} ml="auto">
        <WrapItem>
          <Tooltip label="Heatmap density overlay" hasArrow>
            <Tag
              size="sm"
              variant={overlayMode === 'heatmap' ? 'solid' : 'subtle'}
              colorScheme="orange"
              cursor="pointer"
              onClick={() => {
                const next = overlayMode === 'heatmap' ? 'none' : 'heatmap';
                setOverlayMode(next);
                // keep heatmap visibility in sync
                setHeatmap(next === 'heatmap');
              }}
            >
              Heatmap
            </Tag>
          </Tooltip>
        </WrapItem>
        <WrapItem>
          <Tooltip label="Terrain overlay" hasArrow>
            <Tag
              size="sm"
              variant={overlayMode === 'terrain' ? 'solid' : 'subtle'}
              colorScheme="green"
              cursor="pointer"
              onClick={() => {
                const next = overlayMode === 'terrain' ? 'none' : 'terrain';
                setOverlayMode(next);
                if (next === 'heatmap') setHeatmap(true);
              }}
            >
              Terrain
            </Tag>
          </Tooltip>
        </WrapItem>
        <WrapItem>
          <Tooltip label="Voronoi cluster boundaries" hasArrow>
            <Tag
              size="sm"
              variant={showVoronoi ? 'solid' : 'subtle'}
              colorScheme="blue"
              cursor="pointer"
              onClick={() => setShowVoronoi(!showVoronoi)}
            >
              Voronoi
            </Tag>
          </Tooltip>
        </WrapItem>
      </Wrap>

      {/* Blur Radius when terrain */}
      {overlayMode === 'terrain' && (
        <HStack spacing={2} minW="160px" align="center">
          <Text fontSize="xs" whiteSpace="nowrap">Blur</Text>
          <Slider
            aria-label="Blur radius"
            min={10}
            max={100}
            step={1}
            value={heatmapOpacity}
            onChange={setHeatmapOpacity}
            w="120px"
          >
            <SliderTrack><SliderFilledTrack /></SliderTrack>
            <SliderThumb boxSize={3} />
          </Slider>
        </HStack>
      )}
    </HStack>
  );
}; 