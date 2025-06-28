// Polyfill for structuredClone in Node.js environment
if (typeof globalThis.structuredClone === 'undefined') {
  globalThis.structuredClone = function structuredClone(value: unknown): unknown {
    if (value === null || value === undefined) {
      return value;
    }

    try {
      // For objects and arrays, use JSON methods
      if (typeof value === 'object') {
        return JSON.parse(JSON.stringify(value));
      }

      // For primitive values, return directly
      return value;
    } catch (error) {
      console.warn('structuredClone polyfill failed:', error);

      // Return a shallow copy as fallback
      return Array.isArray(value) ? [...value] : { ...value };
    }
  };
} 