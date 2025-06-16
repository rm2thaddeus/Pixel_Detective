'use client';

// Import polyfill first
import '@/lib/polyfills';
import { ChakraProvider, extendTheme, type ThemeConfig } from '@chakra-ui/react';
import { ReactNode, useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Create a client
const queryClient = new QueryClient();

// Define a minimal, server-safe theme config. This avoids generating
// style tags on the server that would cause a hydration mismatch.
const ssrConfig: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

const ssrTheme = extendTheme({ config: ssrConfig });

// Define the full client-side theme with semantic tokens and system detection
const clientTheme = extendTheme({
  config: {
    initialColorMode: 'system',
    useSystemColorMode: true,
  },
  semanticTokens: {
    colors: {
      pageBg: { default: 'gray.50', _dark: 'gray.900' },
      cardBg: { default: 'white', _dark: 'gray.800' },
      cardPreviewBg: { default: 'gray.100', _dark: 'gray.700' },
      border: { default: 'gray.200', _dark: 'gray.600' },
      textPrimary: { default: 'gray.800', _dark: 'white' },
      textSecondary: { default: 'gray.600', _dark: 'gray.400' },
    },
  },
});

interface ProviderProps {
  children: ReactNode;
}

export function Provider({ children }: ProviderProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  
  // On the server, and for the initial client render, use the minimal SSR theme.
  // After mounting, switch to the full client theme to enable system color mode.
  const theme = mounted ? clientTheme : ssrTheme;

  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>{children}</ChakraProvider>
    </QueryClientProvider>
  );
}