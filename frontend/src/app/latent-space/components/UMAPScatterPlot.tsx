'use client';

import React, { useMemo } from 'react';
import { Box, Spinner, Center } from '@chakra-ui/react';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer } from '@deck.gl/layers';
import { UMAPProjectionResponse, UMAPPoint } from '../types/latent-space';
import { scaleLinear } from 'd3-scale'; // Using d3-scale for color interpolation

interface UMAPScatterPlotProps {
  data: UMAPProjectionResponse | null;
  onPointHover?: (point: UMAPPoint | null) => void;
  onPointClick?: (point: UMAPPoint) => void;
  selectedClusterId?: number | null;
}

const INITIAL_VIEW_STATE = {
  longitude: 0,
  latitude: 0,
  zoom: 1,
  pitch: 0,
  bearing: 0,
};

// Define the purple-to-yellow color scale
const purpleYellow = scaleLinear<string>()
  .domain([0, 1])
  .range(['#5B2C6F', '#F1C40F']);


export function UMAPScatterPlot({
  data,
  onPointHover,
  onPointClick,
  selectedClusterId,
}: UMAPScatterPlotProps) {

  const layers = useMemo(() => {
    if (!data?.points) return [];

    const nClusters = data.clustering_info?.n_clusters ?? 1;
    const colorScale = (clusterId: number) => purpleYellow(clusterId / Math.max(1, nClusters -1));

    return [
      new ScatterplotLayer<UMAPPoint>({
        id: 'scatterplot-layer',
        data: data.points,
        getPosition: d => [d.x, d.y, 0],
        getFillColor: d => {
          if (d.is_outlier) return [128, 128, 128, 150]; // Grey for outliers
          if (d.cluster_id === undefined) return [150, 150, 150, 200];
          
          const color = colorScale(d.cluster_id);
          const rgb = color.substring(4, color.length-1).replace(/ /g, '').split(',').map(Number);
          
          // Dim non-selected clusters
          if (selectedClusterId !== null && d.cluster_id !== selectedClusterId) {
            return [...rgb, 50];
          }

          return [...rgb, 220];
        },
        getRadius: 8, // Adjust for visual preference
        pointRadiusMinPixels: 2,
        pointRadiusMaxPixels: 15,
        pickable: true,
        onHover: info => onPointHover?.(info.object as UMAPPoint),
        onClick: info => onPointClick?.(info.object as UMAPPoint),
        
        // Performance and aesthetics from research
        parameters: {
          blend: true,
          // Additive blending for highlighting dense areas
          blendEquation: 'FUNC_ADD',
          blendFunc: ['SRC_ALPHA', 'ONE', 'ONE', 'ONE_MINUS_SRC_ALPHA'],
        }
      }),
    ];
  }, [data, onPointHover, onPointClick, selectedClusterId]);

  if (!data) {
    return (
      <Center h={600} bg="gray.50" borderRadius="md">
        <Spinner size="xl" />
      </Center>
    );
  }
  
  return (
    <Box position="relative" h="70vh" bg="transparent" borderRadius="md">
      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      >
      </DeckGL>
    </Box>
  );
} 