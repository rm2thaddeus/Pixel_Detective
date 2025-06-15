'use client'

// Import polyfill first
import '@/lib/polyfills'
import { ChakraProvider, extendTheme, type ThemeConfig } from '@chakra-ui/react'
import { ReactNode, useState, useEffect } from 'react'

// HYDRATION FIX: Use mounted state to prevent server/client mismatch
const config: ThemeConfig = {
  initialColorMode: 'light',      // Use light as safe default for SSR
  useSystemColorMode: false,      // Disable system detection during SSR
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

interface ProviderProps {
  children: ReactNode
}

export function Provider({ children }: ProviderProps) {
  const [mounted, setMounted] = useState(false)

  // HYDRATION FIX: Only enable full theme features after client-side hydration
  useEffect(() => {
    setMounted(true)
  }, [])

  // During SSR and initial hydration, render with minimal theme
  if (!mounted) {
    return (
      <ChakraProvider theme={theme}>
        {children}
      </ChakraProvider>
    )
  }

  // After hydration, render with full theme capabilities
  const clientTheme = extendTheme({
    config: {
      initialColorMode: 'system',     // Enable system detection after hydration
      useSystemColorMode: true,       // Enable system detection after hydration
      disableTransitionOnChange: false,
    },
    styles: {
      global: (props: GlobalStyleProps) => ({
        body: {
          bg: props.colorMode === 'dark' ? 'gray.900' : 'white',
          color: props.colorMode === 'dark' ? 'white' : 'gray.800',
        },
      }),
    },
  })

  return (
    <ChakraProvider theme={clientTheme}>
      {children}
    </ChakraProvider>
  )
} 