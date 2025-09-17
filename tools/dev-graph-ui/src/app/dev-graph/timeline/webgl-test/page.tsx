'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Box, VStack, Text, Alert, AlertIcon, Button } from '@chakra-ui/react';

export default function WebGL2TestPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [testResults, setTestResults] = useState<string[]>([]);
  const [isSupported, setIsSupported] = useState<boolean | null>(null);

  const addResult = (message: string) => {
    setTestResults(prev => [...prev, message]);
    console.log(`WebGL2 Test: ${message}`);
  };

  useEffect(() => {
    const runTests = async () => {
      setTestResults([]);
      addResult('Starting WebGL2 diagnostic tests...');

      // Test 1: Basic WebGL2 support
      try {
        const canvas = canvasRef.current;
        if (!canvas) {
          addResult('❌ Canvas element not found');
          return;
        }

        addResult('✅ Canvas element found');

        // Test 2: WebGL2 context creation
        const gl = canvas.getContext('webgl2');
        if (!gl) {
          addResult('❌ WebGL2 context creation failed');
          setIsSupported(false);
          return;
        }

        addResult('✅ WebGL2 context created successfully');

        // Test 3: WebGL2 context with specific attributes
        const gl2 = canvas.getContext('webgl2', {
          powerPreference: 'high-performance',
          antialias: false,
          preserveDrawingBuffer: false,
          alpha: true,
          depth: false,
          stencil: false,
          desynchronized: true
        });

        if (!gl2) {
          addResult('❌ WebGL2 context with specific attributes failed');
        } else {
          addResult('✅ WebGL2 context with specific attributes created');
        }

        // Test 4: Shader compilation
        const vertexShaderSource = `#version 300 es
in vec2 a_position;
in vec3 a_color;
in float a_size;
in float a_kind;

uniform vec2 u_resolution;
uniform float u_zoom;
uniform vec2 u_pan;

out vec3 v_color;
out float v_size;
out float v_kind;

void main() {
  vec2 position = (a_position + u_pan) * u_zoom;
  vec2 clipSpace = ((position / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
  float s = a_size * u_zoom;
  s = clamp(s, 1.0, 36.0);
  gl_PointSize = s;
  v_color = a_color;
  v_size = a_size;
  v_kind = a_kind;
}`;

        const fragmentShaderSource = `#version 300 es
precision highp float;

in vec3 v_color;
in float v_size;
in float v_kind;

out vec4 fragColor;

void main() {
  vec2 center = gl_PointCoord - 0.5;
  float dist = length(center);
  if (dist > 0.5) { discard; }

  float core = 1.0 - smoothstep(0.18, 0.5, dist);
  float border = smoothstep(0.38, 0.5, dist);
  vec3 color = mix(v_color * 1.35, v_color, border);
  float alpha = max(0.15, core * 0.95);

  if (v_kind > 0.5) {
    float rim = smoothstep(0.44, 0.48, dist) * (1.0 - smoothstep(0.48, 0.5, dist));
    float nucleus = 1.0 - smoothstep(0.0, 0.18, dist);
    color = mix(color, vec3(1.0, 0.95, 0.98), rim * 0.8);
    color = mix(color, vec3(0.95, 0.85, 1.0), nucleus * 0.4);
    alpha = max(alpha, rim * 0.9);
  }
  fragColor = vec4(color, alpha);
}`;

        // Create vertex shader
        const vertexShader = gl.createShader(gl.VERTEX_SHADER);
        if (!vertexShader) {
          addResult('❌ Failed to create vertex shader');
          return;
        }
        gl.shaderSource(vertexShader, vertexShaderSource);
        gl.compileShader(vertexShader);
        if (!gl.getShaderParameter(vertexShader, gl.COMPILE_STATUS)) {
          const error = gl.getShaderInfoLog(vertexShader);
          addResult(`❌ Vertex shader compilation failed: ${error}`);
          return;
        }
        addResult('✅ Vertex shader compiled successfully');

        // Create fragment shader
        const fragmentShader = gl.createShader(gl.FRAGMENT_SHADER);
        if (!fragmentShader) {
          addResult('❌ Failed to create fragment shader');
          return;
        }
        gl.shaderSource(fragmentShader, fragmentShaderSource);
        gl.compileShader(fragmentShader);
        if (!gl.getShaderParameter(fragmentShader, gl.COMPILE_STATUS)) {
          const error = gl.getShaderInfoLog(fragmentShader);
          addResult(`❌ Fragment shader compilation failed: ${error}`);
          return;
        }
        addResult('✅ Fragment shader compiled successfully');

        // Create program
        const program = gl.createProgram();
        if (!program) {
          addResult('❌ Failed to create program');
          return;
        }
        gl.attachShader(program, vertexShader);
        gl.attachShader(program, fragmentShader);
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
          const error = gl.getProgramInfoLog(program);
          addResult(`❌ Program linking failed: ${error}`);
          return;
        }
        addResult('✅ Program linked successfully');

        // Test 5: Basic rendering
        gl.useProgram(program);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.clearColor(0.1, 0.1, 0.1, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        // Create a simple test point
        const positionBuffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0]), gl.STATIC_DRAW);

        const positionAttribute = gl.getAttribLocation(program, 'a_position');
        gl.enableVertexAttribArray(positionAttribute);
        gl.vertexAttribPointer(positionAttribute, 2, gl.FLOAT, false, 0, 0);

        const resolutionUniform = gl.getUniformLocation(program, 'u_resolution');
        const zoomUniform = gl.getUniformLocation(program, 'u_zoom');
        const panUniform = gl.getUniformLocation(program, 'u_pan');

        gl.uniform2f(resolutionUniform, canvas.width, canvas.height);
        gl.uniform1f(zoomUniform, 1.0);
        gl.uniform2f(panUniform, 0, 0);

        // Draw a test point
        gl.drawArrays(gl.POINTS, 0, 1);
        addResult('✅ Basic rendering test completed');

        // Test 6: Check WebGL2 specific features
        const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        const maxVertexAttribs = gl.getParameter(gl.MAX_VERTEX_ATTRIBS);
        const maxVertexUniformVectors = gl.getParameter(gl.MAX_VERTEX_UNIFORM_VECTORS);
        const maxFragmentUniformVectors = gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS);

        addResult(`📊 Max texture size: ${maxTextureSize}`);
        addResult(`📊 Max vertex attributes: ${maxVertexAttribs}`);
        addResult(`📊 Max vertex uniform vectors: ${maxVertexUniformVectors}`);
        addResult(`📊 Max fragment uniform vectors: ${maxFragmentUniformVectors}`);

        // Test 7: Check for WebGL2 specific extensions
        const extensions = gl.getSupportedExtensions();
        const webgl2Extensions = extensions?.filter(ext => ext.includes('EXT') || ext.includes('OES') || ext.includes('WEBGL'));
        addResult(`📊 Supported extensions: ${webgl2Extensions?.length || 0}`);

        addResult('🎉 All WebGL2 tests passed!');
        setIsSupported(true);

      } catch (error) {
        addResult(`❌ Test failed with error: ${error}`);
        setIsSupported(false);
      }
    };

    runTests();
  }, []);

  return (
    <Box p={8}>
      <VStack spacing={6} align="stretch">
        <Text fontSize="2xl" fontWeight="bold">
          WebGL2 Diagnostic Test
        </Text>
        
        <Alert status={isSupported === true ? 'success' : isSupported === false ? 'error' : 'info'}>
          <AlertIcon />
          {isSupported === true ? 'WebGL2 is fully supported!' : 
           isSupported === false ? 'WebGL2 has issues - see details below' : 
           'Running WebGL2 tests...'}
        </Alert>

        <Box>
          <Text fontSize="lg" fontWeight="semibold" mb={4}>
            Test Results:
          </Text>
          <VStack spacing={2} align="stretch">
            {testResults.map((result, index) => (
              <Text key={index} fontFamily="mono" fontSize="sm">
                {result}
              </Text>
            ))}
          </VStack>
        </Box>

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
          onClick={() => window.location.reload()}
          colorScheme="blue"
        >
          Run Tests Again
        </Button>

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
