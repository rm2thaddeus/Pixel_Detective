'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Box, Spinner, Text, VStack } from '@chakra-ui/react';

interface SimpleWebGLTimelineProps {
  data: {
    nodes: any[];
    relations: any[];
  };
  width: number;
  height: number;
  currentCommitId?: string;
  colorMode?: 'folder' | 'type' | 'commit-flow' | 'activity' | 'none';
  alwaysShowEdges?: boolean;
  edgeEmphasis?: number; // 0..1
  autoFit?: boolean;
  sizeByLOC?: boolean;
  highlightDocs?: boolean;
  enableZoom?: boolean;
  currentFiles?: { path: string; action: 'created' | 'modified' | 'deleted'; size?: number; lines_after?: number; loc?: number; type?: string }[];
  onCanvasReady?: (canvas: HTMLCanvasElement | null) => void;
}

export default function SimpleWebGLTimeline({
  data,
  width,
  height,
  currentCommitId,
  colorMode = 'folder',
  alwaysShowEdges = true,
  edgeEmphasis = 0.4,
  autoFit = true,
  sizeByLOC = true,
  highlightDocs = true,
  enableZoom = true,
  currentFiles = [],
  onCanvasReady
}: SimpleWebGLTimelineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (onCanvasReady) {
      onCanvasReady(canvasRef.current);
      return () => onCanvasReady(null);
    }
    return () => undefined;
  }, [onCanvasReady]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const animationFrameRef = useRef<number>();
  const physicsRef = useRef<{
    offsetsX: Float32Array;
    offsetsY: Float32Array;
    velX: Float32Array;
    velY: Float32Array;
    particles: Array<{ x: number; y: number; vx: number; vy: number; life: number; r: number; g: number; b: number; size: number }>; 
    pulseLife: Float32Array; // per-node activity pulses (- for delete, + for create/modify)
    lastCommitId?: string;
  }>({
    offsetsX: new Float32Array(0),
    offsetsY: new Float32Array(0),
    velX: new Float32Array(0),
    velY: new Float32Array(0),
    particles: [],
    pulseLife: new Float32Array(0)
  });

  console.log('SimpleWebGLTimeline: Component rendered with', data.nodes.length, 'nodes');

  useEffect(() => {
    if (!data.nodes.length) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl2');
    if (!gl) {
      setError('WebGL2 not supported');
      return;
    }

    // Simple vertex shader
    const vertexShaderSource = `#version 300 es
in vec2 a_position;
in vec3 a_color;
in float a_size;

uniform vec2 u_resolution;
uniform float u_zoom;
uniform vec2 u_pan;

out vec3 v_color;
out float v_size;

void main() {
  vec2 position = (a_position + u_pan) * u_zoom;
  vec2 clipSpace = ((position / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
  gl_PointSize = a_size * u_zoom;
  v_color = a_color;
  v_size = a_size;
}`;

    // Simple fragment shader
    const fragmentShaderSource = `#version 300 es
precision highp float;

in vec3 v_color;
in float v_size;

out vec4 fragColor;

void main() {
  vec2 center = gl_PointCoord - 0.5;
  float dist = length(center);
  if (dist > 0.5) discard;
  
  float alpha = 1.0 - smoothstep(0.3, 0.5, dist);
  fragColor = vec4(v_color, alpha);
}`;

    // Create shaders
    const createShader = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) throw new Error('Failed to create shader');
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const error = gl.getShaderInfoLog(shader);
        gl.deleteShader(shader);
        throw new Error(`Shader compilation failed: ${error}`);
      }
      return shader;
    };

    const createProgram = (vertexShader: WebGLShader, fragmentShader: WebGLShader) => {
      const program = gl.createProgram();
      if (!program) throw new Error('Failed to create program');
      gl.attachShader(program, vertexShader);
      gl.attachShader(program, fragmentShader);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        const error = gl.getProgramInfoLog(program);
        gl.deleteProgram(program);
        throw new Error(`Program linking failed: ${error}`);
      }
      return program;
    };

    try {
      const vertexShader = createShader(gl.VERTEX_SHADER, vertexShaderSource);
      const fragmentShader = createShader(gl.FRAGMENT_SHADER, fragmentShaderSource);
      const program = createProgram(vertexShader, fragmentShader);

      // Set up canvas
      const devicePixelRatio = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
      canvas.width = width * devicePixelRatio;
      canvas.height = height * devicePixelRatio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      gl.viewport(0, 0, canvas.width, canvas.height);

      // Enable blending
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

      // Create buffers
      const positionBuffer = gl.createBuffer();
      const colorBuffer = gl.createBuffer();
      const sizeBuffer = gl.createBuffer();
      const edgePositionBuffer = gl.createBuffer();
      const edgeColorBuffer = gl.createBuffer();

      // Interaction state
      const zoom = { current: 1.0 };
      const pan = { current: { x: 0, y: 0 } };
      let isDragging = false;
      let lastMouse = { x: 0, y: 0 };

      // Mouse handlers
      const onWheel = (e: WheelEvent) => {
        e.preventDefault();
        if (!enableZoom) return;
        const delta = Math.sign(e.deltaY) * 0.1;
        zoom.current = Math.max(0.2, Math.min(4, zoom.current * (1 - delta)));
      };

      const onMouseDown = (e: MouseEvent) => {
        isDragging = true;
        lastMouse = { x: e.clientX, y: e.clientY };
      };

      const onMouseMove = (e: MouseEvent) => {
        if (!isDragging) return;
        const dx = e.clientX - lastMouse.x;
        const dy = e.clientY - lastMouse.y;
        pan.current.x += dx;
        pan.current.y += dy;
        lastMouse = { x: e.clientX, y: e.clientY };
      };

      const onMouseUp = () => {
        isDragging = false;
      };

      canvas.addEventListener('wheel', onWheel, { passive: false });
      canvas.addEventListener('mousedown', onMouseDown);
      canvas.addEventListener('mousemove', onMouseMove);
      canvas.addEventListener('mouseup', onMouseUp);

      // Simple render function
      const render = () => {
        // Clear canvas
        gl.clearColor(0.1, 0.1, 0.2, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        if (data.nodes.length === 0) {
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }

      // Prepare data with commit-chain layout and file clustering
      const positions = new Float32Array(data.nodes.length * 2);
      const colors = new Float32Array(data.nodes.length * 3);
      const sizes = new Float32Array(data.nodes.length);
      const anchorsX = new Float32Array(data.nodes.length);
      const anchorsY = new Float32Array(data.nodes.length);

        const idToIndex = new Map<string, number>();
        data.nodes.forEach((n: any, idx: number) => idToIndex.set(n.id, idx));

        const commits = data.nodes.filter((n: any) => (n.originalType === 'GitCommit' || n.type === 'commit'));
        const commitIndex = new Map<string, number>();
        commits.forEach((c: any, i: number) => commitIndex.set(c.id, i));
        const commitCount = Math.max(1, commits.length);
        // Expand to use nearly full canvas
        const leftPad = 30, rightPad = 30;
        const innerW = Math.max(1, width - leftPad - rightPad);
        const topY = Math.max(60, Math.floor(height * 0.18));
        const minFileY = Math.max(topY + 50, Math.floor(height * 0.45));
        const maxFileY = Math.max(minFileY + 40, height - 60);

        const touchesByFile = new Map<string, number[]>();
        (data.relations || []).forEach((e: any) => {
          if (e.type !== 'touch') return;
          const fromIdx = idToIndex.get(e.from);
          const toIdx = idToIndex.get(e.to);
          if (fromIdx == null || toIdx == null) return;
          const fromNode = data.nodes[fromIdx];
          if (!(fromNode.originalType === 'GitCommit' || fromNode.type === 'commit')) return;
          const arr = touchesByFile.get(e.to) || [];
          arr.push(commitIndex.get(fromNode.id) ?? 0);
          touchesByFile.set(e.to, arr);
        });

        // Current activity maps (for pulses and delete fade)
        const createdNow = new Set((currentFiles || []).filter(f => f.action === 'created').map(f => f.path));
        const modifiedNow = new Set((currentFiles || []).filter(f => f.action === 'modified').map(f => f.path));
        const deletedNow = new Set((currentFiles || []).filter(f => f.action === 'deleted').map(f => f.path));

        data.nodes.forEach((node: any, i: number) => {
          const isCommit = node.originalType === 'GitCommit' || node.type === 'commit';
          const isHighlight = currentCommitId && node.id === currentCommitId;
          if (isCommit) {
            const idx = commitIndex.get(node.id) ?? 0;
            const x = leftPad + (idx * (innerW / Math.max(1, commitCount - 1)));
            anchorsX[i] = x; anchorsY[i] = topY;
            sizes[i] = Math.max(10, node.size ?? 10);
            // commit color
            colors[i * 3] = 0.62; colors[i * 3 + 1] = 0.36; colors[i * 3 + 2] = 0.9;
          } else {
            const touches = touchesByFile.get(node.id) || [Math.floor(commitCount / 2)];
            const avgIdx = touches.reduce((a, b) => a + b, 0) / Math.max(1, touches.length);
            const x = leftPad + (avgIdx * (innerW / Math.max(1, commitCount - 1)));
            anchorsX[i] = x;
            // map file y to 55–90% band with light spread by degree
            const spread = Math.min(1, (touches.length - 1) / 6);
            const baseY = minFileY + spread * (maxFileY - minFileY);
            anchorsY[i] = baseY;
            let baseSize = Math.max(6, node.size ?? 7);
            // activity pulses
            if (createdNow.has(node.id)) baseSize *= 1.25;
            if (modifiedNow.has(node.id)) baseSize *= 1.12;
            if (deletedNow.has(node.id)) baseSize *= 0.6; // will be faded via color too
            sizes[i] = baseSize;
            // color by mode
            const isDoc = node.originalType === 'Document';
            let r = 0.2, g = 0.7, b = 0.9;
            if (colorMode === 'type') { r = isDoc ? 0.2 : 0.2; g = isDoc ? 0.85 : 0.6; b = isDoc ? 0.5 : 0.95; }
            if (colorMode === 'activity') { const t = Math.min(1, Math.log2(1 + (node.touchCount ?? 1)) / 5); r = 0.2 + 0.6 * t; g = 0.4; b = 0.9 - 0.6 * t; }
            if (colorMode === 'folder' && node.folderPath) {
              let h = 0; for (let k = 0; k < node.folderPath.length; k++) h = (h * 31 + node.folderPath.charCodeAt(k)) >>> 0;
              const hue = (h % 360); const s = 0.55, l = 0.55; const a = s * Math.min(l, 1 - l);
              const f = (n: number) => { const K = (n + hue / 30) % 12; const t = l - a * Math.max(-1, Math.min(K - 3, Math.min(9 - K, 1))); return t; };
              r = f(0); g = f(8); b = f(4);
            }
            // deleted fade
            if (deletedNow.has(node.id)) { r *= 0.6; g *= 0.6; b *= 0.6; }
            colors[i * 3] = r; colors[i * 3 + 1] = g; colors[i * 3 + 2] = b;
          }
          if (isHighlight) {
            sizes[i] = Math.max(sizes[i], 16);
            colors[i * 3] = 1.0; colors[i * 3 + 1] = 1.0; colors[i * 3 + 2] = 0.0;
          }
        });

        // --- Light physics pass (files repel, spring to anchors) ---
        {
          const ph = physicsRef.current;
          if (ph.offsetsX.length !== data.nodes.length) {
            ph.offsetsX = new Float32Array(data.nodes.length);
            ph.offsetsY = new Float32Array(data.nodes.length);
            ph.velX = new Float32Array(data.nodes.length);
            ph.velY = new Float32Array(data.nodes.length);
            ph.pulseLife = new Float32Array(data.nodes.length);
          }
          const SPRING = 0.08;
          const DAMP = 0.86;
          const REPULSE = 1200; // strength
          const REPULSE_RADIUS = 90; // px

          // one repulsion sweep among files
          for (let i = 0; i < data.nodes.length; i++) {
            const ni: any = data.nodes[i];
            const isCommitI = ni.originalType === 'GitCommit' || ni.type === 'commit';
            if (isCommitI) continue;
            // spring
            const px = anchorsX[i] + ph.offsetsX[i];
            const py = anchorsY[i] + ph.offsetsY[i];
            const fx = (anchorsX[i] - px) * SPRING;
            const fy = (anchorsY[i] - py) * SPRING;
            ph.velX[i] += fx; ph.velY[i] += fy;
            // repulsion vs other files
            for (let j = i + 1; j < data.nodes.length; j++) {
              const nj: any = data.nodes[j];
              const isCommitJ = nj.originalType === 'GitCommit' || nj.type === 'commit';
              if (isCommitJ) continue;
              const qx = anchorsX[j] + ph.offsetsX[j];
              const qy = anchorsY[j] + ph.offsetsY[j];
              const dx = qx - px; const dy = qy - py; const d2 = dx*dx + dy*dy;
              if (d2 > REPULSE_RADIUS*REPULSE_RADIUS || d2 === 0) continue;
              const d = Math.sqrt(d2);
              const s = (REPULSE / Math.max(8, d2));
              const rx = (dx / (d || 1)) * s; const ry = (dy / (d || 1)) * s;
              ph.velX[i] -= rx; ph.velY[i] -= ry;
              ph.velX[j] += rx; ph.velY[j] += ry;
            }
          }
          // integrate
          for (let i = 0; i < data.nodes.length; i++) {
            const ni: any = data.nodes[i];
            const isCommitI = ni.originalType === 'GitCommit' || ni.type === 'commit';
            if (isCommitI) { ph.offsetsX[i] = 0; ph.offsetsY[i] = 0; ph.velX[i] = 0; ph.velY[i] = 0; continue; }
            ph.velX[i] *= DAMP; ph.velY[i] *= DAMP;
            ph.offsetsX[i] += ph.velX[i]; ph.offsetsY[i] += ph.velY[i];
            // clamp offsets to keep in band
            ph.offsetsY[i] = Math.max(-40, Math.min(40, ph.offsetsY[i]));
            ph.offsetsX[i] = Math.max(-60, Math.min(60, ph.offsetsX[i]));
          }

          // finalize positions from anchors + offsets and compute pulse decay
          for (let i = 0; i < data.nodes.length; i++) {
            positions[i*2] = anchorsX[i] + ph.offsetsX[i];
            positions[i*2+1] = anchorsY[i] + ph.offsetsY[i];
            // decay any existing pulse
            ph.pulseLife[i] *= 0.9;
          }
        }

        // Handle activity: create/modify pulses and delete explosions
        {
          const ph = physicsRef.current;
          if (currentFiles && currentFiles.length && ph.lastCommitId !== currentCommitId) {
            ph.lastCommitId = currentCommitId;
            for (const f of currentFiles) {
              const idx = data.nodes.findIndex((n: any) => n.id === f.path);
              if (idx < 0) continue;
              const cx = positions[idx*2]; const cy = positions[idx*2+1];
              if (f.action === 'deleted') {
                for (let p = 0; p < 14; p++) {
                  const a = Math.random()*Math.PI*2; const sp = 1.5 + Math.random()*3.0;
                  ph.particles.push({ x: cx, y: cy, vx: Math.cos(a)*sp, vy: Math.sin(a)*sp, life: 24, r: 1.0, g: 0.75, b: 0.25, size: 6 });
                }
                ph.pulseLife[idx] = -0.8; // negative pulse shrinks/fades
              } else {
                // positive pulse for create/modify
                ph.pulseLife[idx] = Math.max(ph.pulseLife[idx], f.action === 'created' ? 1.2 : 0.8);
              }
            }
          }
        }

        // Build edge buffers (chain + touch) and draw them first
        const edges = (data.relations || []) as any[];
        if (edges.length > 0) {
          const edgePositions = new Float32Array(edges.length * 4);
          const edgeColors = new Float32Array(edges.length * 6);
          edges.forEach((e: any, idx: number) => {
            const a = idToIndex.get(e.from); const b = idToIndex.get(e.to);
            if (a == null || b == null) return;
            const i4 = idx * 4; const c6 = idx * 6;
            edgePositions[i4] = positions[a * 2]; edgePositions[i4 + 1] = positions[a * 2 + 1];
            edgePositions[i4 + 2] = positions[b * 2]; edgePositions[i4 + 3] = positions[b * 2 + 1];
            const isChain = e.type === 'chain'; const rr = isChain ? 0.55 : 0.55; const gg = isChain ? 0.45 : 0.6; const bb = isChain ? 0.85 : 0.7;
            edgeColors[c6] = rr; edgeColors[c6 + 1] = gg; edgeColors[c6 + 2] = bb;
            edgeColors[c6 + 3] = rr; edgeColors[c6 + 4] = gg; edgeColors[c6 + 5] = bb;
          });
          // Tiny line shader program per frame (ok for now)
          const lineVS = `#version 300 es\n in vec2 a_position; in vec3 a_color; uniform vec2 u_resolution; uniform float u_zoom; uniform vec2 u_pan; out vec3 v_color; void main(){ vec2 p=(a_position+u_pan)*u_zoom; vec2 cs=((p/u_resolution)*2.0)-1.0; gl_Position=vec4(cs*vec2(1,-1),0,1); v_color=a_color; }`;
          const lineFS = `#version 300 es\n precision highp float; in vec3 v_color; out vec4 fragColor; void main(){ fragColor=vec4(v_color, 0.45); }`;
          const lvs = createShader(gl.VERTEX_SHADER, lineVS);
          const lfs = createShader(gl.FRAGMENT_SHADER, lineFS);
          const lp = createProgram(lvs, lfs);
          gl.useProgram(lp);
          const rLoc = gl.getUniformLocation(lp, 'u_resolution');
          const zLoc = gl.getUniformLocation(lp, 'u_zoom');
          const pLoc = gl.getUniformLocation(lp, 'u_pan');
          gl.uniform2f(rLoc, canvas.width, canvas.height);
          gl.uniform1f(zLoc, zoom.current);
          gl.uniform2f(pLoc, pan.current.x, pan.current.y);
          gl.bindBuffer(gl.ARRAY_BUFFER, edgePositionBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, edgePositions, gl.STATIC_DRAW);
          const ap = gl.getAttribLocation(lp, 'a_position'); gl.enableVertexAttribArray(ap); gl.vertexAttribPointer(ap, 2, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ARRAY_BUFFER, edgeColorBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, edgeColors, gl.STATIC_DRAW);
          const ac = gl.getAttribLocation(lp, 'a_color'); gl.enableVertexAttribArray(ac); gl.vertexAttribPointer(ac, 3, gl.FLOAT, false, 0, 0);
          gl.drawArrays(gl.LINES, 0, edges.length * 2);
        }

        // Upload data to GPU (nodes + particles)
        let extraPositions: Float32Array | null = null;
        let extraColors: Float32Array | null = null;
        let extraSizes: Float32Array | null = null;
        {
          const ph = physicsRef.current;
          if (ph.particles.length > 0) {
            // update particles
            const alive: typeof ph.particles = [];
            for (const pt of ph.particles) {
              pt.x += pt.vx; pt.y += pt.vy; pt.vy += 0.08; // slight gravity
              pt.life -= 1;
              if (pt.life > 0) alive.push(pt);
            }
            ph.particles = alive.slice(0, 300);
            const m = ph.particles.length;
            if (m > 0) {
              extraPositions = new Float32Array(m*2);
              extraColors = new Float32Array(m*3);
              extraSizes = new Float32Array(m);
              for (let i = 0; i < m; i++) {
                const pt = ph.particles[i];
                extraPositions[i*2] = pt.x; extraPositions[i*2+1] = pt.y;
                const fade = Math.max(0.2, pt.life/22);
                extraColors[i*3] = pt.r; extraColors[i*3+1] = pt.g; extraColors[i*3+2] = pt.b;
                extraSizes[i] = pt.size * fade;
              }
            }
          }
        }

        // Apply pulse to sizes and color vibrance
        {
          const ph = physicsRef.current;
          for (let i = 0; i < data.nodes.length; i++) {
            const pulse = ph.pulseLife[i] || 0;
            if (pulse !== 0) {
              const k = pulse > 0 ? (1 + Math.min(0.35, pulse)) : (1 + Math.max(-0.35, pulse));
              sizes[i] *= k;
              const c0 = colors[i*3], c1 = colors[i*3+1], c2 = colors[i*3+2];
              const boost = pulse > 0 ? 1.0 + Math.min(0.25, pulse*0.3) : 1.0 + Math.max(-0.4, pulse*0.5);
              colors[i*3] = Math.min(1, c0*boost);
              colors[i*3+1] = Math.min(1, c1*boost);
              colors[i*3+2] = Math.min(1, c2*boost);
            }
          }
        }

        const totalCount = data.nodes.length + (extraSizes ? extraSizes.length : 0);
        const drawPositions = totalCount === data.nodes.length ? positions : (() => { const out = new Float32Array(totalCount*2); out.set(positions); if (extraPositions) out.set(extraPositions, positions.length); return out; })();
        const drawColors = totalCount === data.nodes.length ? colors : (() => { const out = new Float32Array(totalCount*3); out.set(colors); if (extraColors) out.set(extraColors, colors.length); return out; })();
        const drawSizes = totalCount === data.nodes.length ? sizes : (() => { const out = new Float32Array(totalCount); out.set(sizes); if (extraSizes) out.set(extraSizes, sizes.length); return out; })();

        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, drawPositions, gl.STATIC_DRAW);

        gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, drawColors, gl.STATIC_DRAW);

        gl.bindBuffer(gl.ARRAY_BUFFER, sizeBuffer);
        gl.bufferData(gl.ARRAY_BUFFER, drawSizes, gl.STATIC_DRAW);

        // Use program
        gl.useProgram(program);

        // Set uniforms
        const resolutionUniform = gl.getUniformLocation(program, 'u_resolution');
        const zoomUniform = gl.getUniformLocation(program, 'u_zoom');
        const panUniform = gl.getUniformLocation(program, 'u_pan');

        gl.uniform2f(resolutionUniform, canvas.width, canvas.height);
        gl.uniform1f(zoomUniform, zoom.current);
        gl.uniform2f(panUniform, pan.current.x, pan.current.y);

        // Set up attributes
        const positionAttribute = gl.getAttribLocation(program, 'a_position');
        const colorAttribute = gl.getAttribLocation(program, 'a_color');
        const sizeAttribute = gl.getAttribLocation(program, 'a_size');

        gl.enableVertexAttribArray(positionAttribute);
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.vertexAttribPointer(positionAttribute, 2, gl.FLOAT, false, 0, 0);

        gl.enableVertexAttribArray(colorAttribute);
        gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
        gl.vertexAttribPointer(colorAttribute, 3, gl.FLOAT, false, 0, 0);

        gl.enableVertexAttribArray(sizeAttribute);
        gl.bindBuffer(gl.ARRAY_BUFFER, sizeBuffer);
        gl.vertexAttribPointer(sizeAttribute, 1, gl.FLOAT, false, 0, 0);

        // Draw points
        gl.drawArrays(gl.POINTS, 0, totalCount);

        // Continue render loop
        animationFrameRef.current = requestAnimationFrame(render);
      };

      // Start render loop
      setIsLoading(false);
      render();

      // Cleanup
      return () => {
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }
        canvas.removeEventListener('wheel', onWheel);
        canvas.removeEventListener('mousedown', onMouseDown);
        canvas.removeEventListener('mousemove', onMouseMove);
        canvas.removeEventListener('mouseup', onMouseUp);
      };

    } catch (err) {
      console.error('WebGL2 setup failed:', err);
      setError(err instanceof Error ? err.message : 'WebGL2 setup failed');
      setIsLoading(false);
    }
  }, [data, width, height, currentCommitId]);

  if (error) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" height={height}>
        <Text color="red.500">Error: {error}</Text>
      </Box>
    );
  }

  return (
    <Box position="relative" width={`${width}px`} height={`${height}px`}>
      <canvas
        ref={canvasRef}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          cursor: 'grab',
          display: 'block'
        }}
      />
      {isLoading && (
        <Box position="absolute" top="0" left="0" right="0" bottom="0" display="flex" alignItems="center" justifyContent="center">
          <VStack spacing={4}>
            <Spinner size="xl" color="teal.500" />
            <Text>Loading WebGL2 Timeline...</Text>
          </VStack>
        </Box>
      )}
    </Box>
  );
}
