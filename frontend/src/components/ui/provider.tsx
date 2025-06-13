'use client'

// Import polyfill first
import '@/lib/polyfills'
import { ChakraProvider, createSystem, defaultConfig } from '@chakra-ui/react'
import { ReactNode } from 'react'

// Create a system configuration for Chakra UI v3
const system = createSystem(defaultConfig)

export function Provider({ children }: { children: ReactNode }) {
  return (
    <ChakraProvider value={system}>
      {children}
    </ChakraProvider>
  )
} 