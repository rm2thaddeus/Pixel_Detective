'use client'

import { IconButton, useColorMode, useColorModeValue } from '@chakra-ui/react'
import { FiSun, FiMoon } from 'react-icons/fi'
import { useState, useEffect } from 'react'

export function ThemeToggle() {
  const { colorMode, toggleColorMode } = useColorMode()
  const [mounted, setMounted] = useState(false)

  // Prevent hydration mismatch
  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    // Return a placeholder during SSR to prevent hydration mismatch
    return (
      <IconButton
        aria-label="Toggle theme"
        icon={<FiSun />}
        variant="ghost"
        size="md"
        disabled
      />
    )
  }
  
  const icon = useColorModeValue(<FiMoon />, <FiSun />)
  const label = useColorModeValue('Switch to dark mode', 'Switch to light mode')

  return (
    <IconButton
      aria-label={label}
      icon={icon}
      onClick={toggleColorMode}
      variant="ghost"
      size="md"
      transition="all 0.2s"
      _hover={{
        bg: useColorModeValue('gray.100', 'gray.700'),
        transform: 'scale(1.1)',
      }}
    />
  )
} 