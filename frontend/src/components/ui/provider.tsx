'use client'

// Import polyfill first
import '@/lib/polyfills'
import { ChakraProvider, extendTheme, type ThemeConfig } from '@chakra-ui/react'
import { ReactNode } from 'react'

// 1. Create a theme configuration
const config: ThemeConfig = {
  initialColorMode: 'light', // Start with light to prevent hydration mismatch
  useSystemColorMode: false, // Disable to prevent SSR/client mismatch
  disableTransitionOnChange: false,
}

interface GlobalStyleProps {
  colorMode: 'light' | 'dark'
}

// 2. Extend the theme to include the color mode config
const theme = extendTheme({
  config,
  styles: {
    global: (props: GlobalStyleProps) => ({
      body: {
        bg: props.colorMode === 'dark' ? 'gray.900' : 'white',
        color: props.colorMode === 'dark' ? 'white' : 'gray.800',
      },
    }),
  },
})

export function Provider({ children }: { children: ReactNode }) {
  return (
    <ChakraProvider theme={theme}>
      {children}
    </ChakraProvider>
  )
} 