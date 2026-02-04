'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Box, VStack, Text, Button } from '@chakra-ui/react';

export default function WebGL2SimpleTestPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState<string>('Initializing...');
  const [frameCount, setFrameCount] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl2');
    if (!gl) {
      setStatus('WebGL2 not supported');
      return;
    }

    setStatus('WebGL2 context created');

    // Simple vertex shader
    const vertexShaderSource = `#version 300 es
in vec2 a_position;
uniform vec2 u_resolution;

void main() {
  vec2 clipSpace = ((a_position / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
  gl_PointSize = 20.0;
}`;

    // Simple fragment shader
    const fragmentShaderSource = `#version 300 es
precision highp float;
out vec4 fragColor;

void main() {
  fragColor = vec4(1.0, 0.0, 0.0, 1.0); // Red color
}`;

    // Create shaders
    const vertexShader = gl.createShader(gl.VERTEX_SHADER);
    if (!vertexShader) {
      setStatus('Failed to create vertex shader');
      return;
    }
    gl.shaderSource(vertexShader, vertexShaderSource);
    gl.compileShader(vertexShader);
    if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(vertexShader);
      setStatus(`Vertex shader error: ${error}`);
      return;
    }

    const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
    if (!fragmentShader) {
      setStatus('Failed to create fragment shader');
      return;
    }
    gl.shaderSource(fragmentShader, fragmentShaderSource);
    gl.compileShader(fragmentShader);
    if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(fragmentShader);
      setStatus(`Fragment shader error: ${error}`);
      return;
    }

    // Create program
    const program = gl.createProgram();
    if (!program) {
      setStatus('Failed to create program');
      return;
    }
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      setStatus(`Program linking error: ${error}`);
      return;
    }

    setStatus('Shaders compiled successfully');

    // Create buffer with test points
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      100, 100,  // Point 1
      200, 150,  // Point 2
      300, 200,  // Point 3
    ]), gl.STATIC_DRAW);

    // Get attribute and uniform locations
    const positionAttribute = gl.getAttribLocation(program, 'a_position');
    const resolutionUniform = gl.getUniformLocation(program, 'u_resolution');

    // Set up viewport
    gl.viewport(0, 0, canvas.width, canvas.height);

    // Render loop
    let frameCount = 0;
    const render = () => {
      // Clear canvas
      gl.clearColor(0.1, 0.1, 0.3, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      // Use program
      gl.useProgram(program);

      // Set uniforms
      gl.uniform2f(resolutionUniform, canvas.width, canvas.height);

      // Set up attributes
      gl.enableVertexAttribArray(positionAttribute);
      gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
      gl.vertexAttribPointer(positionAttribute, 2, gl.FLOAT, false, 0, 0);

      // Draw points
      gl.drawArrays(gl.POINTS, 0, 3);

      frameCount++;
      setFrameCount(frameCount);
      setStatus(`Rendering... Frame ${frameCount}`);

      // Continue loop
      requestAnimationFrame(render);
    };

    // Start render loop
    render();
    setStatus('Render loop started');

  }, []);

  return (
    <Box p={8}>
      <VStack spacing={6} align="stretch">
        <Text fontSize="2xl" fontWeight="bold">
          Simple WebGL2 Test
        </Text>
        
        <Text fontSize="lg">
          Status: {status}
        </Text>

        <Text fontSize="sm" color="gray.500">
          Frame Count: {frameCount}
        </Text>

        <canvas
          ref={canvasRef}
          width={400}
          height={300}
          style={{
            border: '1px solid #ccc',
            backgroundColor: '#1a1a1a'
          }}
        />

        <Button
          onClick={() => window.location.href = '/dev-graph/timeline/webgl'}
          colorScheme="teal"
        >
          Go to WebGL2 Timeline
        </Button>
      </VStack>
    </Box>
  );
}
