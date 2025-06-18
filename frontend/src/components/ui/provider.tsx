'use client';

// Import polyfill first
import '@/lib/polyfills';
import { ChakraProvider, extendTheme } from '@chakra-ui/react';
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Create a client
const queryClient = new QueryClient();

// Define the theme with semantic tokens
const theme = extendTheme({
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false,
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
  return (
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme} suppressHydrationWarning>
        {children}
      </ChakraProvider>
    </QueryClientProvider>
  );
}