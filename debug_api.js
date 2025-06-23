// Debug script to test UMAP API endpoint
const API_BASE_URL = 'http://localhost:8002';

async function testUMAPAPI() {
  try {
    console.log('🔍 Testing UMAP API endpoint...');
    
    // For Node.js versions that don't have fetch built-in
    let fetchFn;
    try {
      fetchFn = fetch;
    } catch {
      // Try to use node-fetch if available
      try {
        const nodeFetch = require('node-fetch');
        fetchFn = nodeFetch;
      } catch {
        console.log('❌ fetch not available. Please use Node 18+ or install node-fetch');
        return;
      }
    }
    
    // First, check if backend is responding
    console.log('🏥 Checking backend health...');
    const healthResponse = await fetchFn(`${API_BASE_URL}/health`);
    const healthData = await healthResponse.json();
    console.log('✅ Health check:', healthData);
    
    // Test the UMAP projection endpoint 
    console.log('🎯 Testing UMAP projection endpoint...');
    const umapResponse = await fetchFn(`${API_BASE_URL}/umap/projection?sample_size=25`);
    
    if (!umapResponse.ok) {
      console.error('❌ UMAP API failed:', umapResponse.status, umapResponse.statusText);
      const errorText = await umapResponse.text();
      console.error('Error response:', errorText);
      return;
    }
    
    const umapData = await umapResponse.json();
    console.log('✅ UMAP API Response structure:');
    console.log('📊 Points count:', umapData.points?.length);
    console.log('🏷️ Collection:', umapData.collection);
    console.log('🎨 Clustering info:', umapData.clustering_info);
    
    // Check individual point structure
    if (umapData.points && umapData.points.length > 0) {
      const samplePoint = umapData.points[0];
      console.log('🔍 Sample point structure:', {
        id: samplePoint.id?.slice(0, 8) + '...',
        hasXY: typeof samplePoint.x === 'number' && typeof samplePoint.y === 'number',
        hasClusterId: 'cluster_id' in samplePoint,
        hasIsOutlier: 'is_outlier' in samplePoint,
        hasThumbnail: 'thumbnail_base64' in samplePoint,
        hasFilename: 'filename' in samplePoint,
        allKeys: Object.keys(samplePoint)
      });
      
      console.log('🎯 First 3 points coordinates:');
      umapData.points.slice(0, 3).forEach((point, i) => {
        console.log(`  Point ${i + 1}: x=${point.x?.toFixed(2)}, y=${point.y?.toFixed(2)}, id=${point.id?.slice(0, 8)}`);
      });
    } else {
      console.log('❌ No points returned in response');
    }
    
  } catch (error) {
    console.error('❌ API Test failed:', error.message);
    console.error('Stack:', error.stack);
  }
}

// Run the test
console.log('🚀 Starting UMAP API Debug Test...');
testUMAPAPI();

// Debug script to test WebGL and DeckGL issues
console.log('🧪 Starting WebGL and DeckGL debugging...');

// Test 1: Check WebGL support
function testWebGL() {
  console.log('🎮 Testing WebGL support...');
  
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (gl) {
      console.log('✅ WebGL is supported');
      console.log('🔍 WebGL info:', {
        version: gl.getParameter(gl.VERSION),
        vendor: gl.getParameter(gl.VENDOR),
        renderer: gl.getParameter(gl.RENDERER),
        shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
        maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
        maxVertexAttribs: gl.getParameter(gl.MAX_VERTEX_ATTRIBS)
      });
      return true;
    } else {
      console.log('❌ WebGL is not supported');
      return false;
    }
  } catch (error) {
    console.log('❌ WebGL test failed:', error);
    return false;
  }
}

// Test 2: Check if DeckGL canvas exists
function checkDeckGLCanvas() {
  console.log('🎨 Checking for DeckGL canvas...');
  
  const canvases = document.querySelectorAll('canvas');
  console.log(`📊 Found ${canvases.length} canvas elements:`, Array.from(canvases).map(c => ({
    width: c.width,
    height: c.height,
    style: c.style.cssText,
    context: c.getContext('webgl') ? 'WebGL' : 'Other'
  })));
  
  return canvases.length > 0;
}

// Test 3: Check for DeckGL div container
function checkDeckGLContainer() {
  console.log('📦 Checking for DeckGL container...');
  
  const containers = document.querySelectorAll('[class*="deck"], [id*="deck"]');
  console.log(`📊 Found ${containers.length} potential DeckGL containers:`, Array.from(containers).map(c => ({
    className: c.className,
    id: c.id,
    children: c.children.length
  })));
}

// Run tests
testWebGL();
checkDeckGLCanvas();
checkDeckGLContainer();

console.log('🔍 Debugging complete. Check results above.'); 