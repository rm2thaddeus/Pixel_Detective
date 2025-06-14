"use client"

import type { IconButtonProps } from "@chakra-ui/react"
import { IconButton, useColorMode, useColorModeValue } from "@chakra-ui/react"
import * as React from "react"
import { LuMoon, LuSun } from "react-icons/lu"

export function ColorModeIcon() {
  const { colorMode } = useColorMode()
  return colorMode === "dark" ? <LuSun /> : <LuMoon />
}

type ColorModeButtonProps = Omit<IconButtonProps, "aria-label"> & {
  // Custom props can be added here if needed
}

export const ColorModeButton = React.forwardRef<
  HTMLButtonElement,
  ColorModeButtonProps
>(function ColorModeButton(props, ref) {
  const { toggleColorMode } = useColorMode()

  return (
    <IconButton
      onClick={toggleColorMode}
      variant="ghost"
      aria-label="Toggle color mode"
      size="sm"
      ref={ref}
      transition="all 0.2s"
      _hover={{
        bg: useColorModeValue('gray.100', 'gray.700'),
        transform: 'scale(1.1)',
      }}
      {...props}
    >
      <ColorModeIcon />
    </IconButton>
  )
})

// Export Chakra UI's built-in hooks for consistency
export { useColorMode, useColorModeValue } from "@chakra-ui/react"
