# Dark Mode Implementation Requirements - Sprint 10 Phase 2

> **Priority:** High - Critical user requirement for extended sprint  
> **Status:** 🔄 Not Started  
> **Estimated Effort:** 1-2 days  

---

## 1. Overview

Dark mode is a critical requirement for modern web applications. Users expect seamless theme switching with proper contrast ratios, system preference detection, and instant visual feedback.

### Success Criteria
- [ ] Instant theme toggle (≤ 100ms)
- [ ] System preference detection on first visit
- [ ] User preference persistence across sessions
- [ ] All components support both light and dark modes
- [ ] Proper contrast ratios (WCAG AA compliance)
- [ ] Smooth transitions between themes

---

## 2. Technical Implementation

### 2.1 Chakra UI Color Mode Setup

**File:** `frontend/src/components/ui/provider.tsx`

```tsx
'use client'

import { ChakraProvider, ColorModeScript } from '@chakra-ui/react'
import { extendTheme, type ThemeConfig } from '@chakra-ui/react'

const config: ThemeConfig = {
  initialColorMode: 'system', // 'dark' | 'light' | 'system'
  useSystemColorMode: true,
}

const theme = extendTheme({
  config,
  colors: {
    // Custom color palette for both modes
    brand: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
    },
  },
  styles: {
    global: (props: any) => ({
      body: {
        bg: props.colorMode === 'dark' ? 'gray.900' : 'white',
        color: props.colorMode === 'dark' ? 'white' : 'gray.900',
      },
    }),
  },
})

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <ChakraProvider theme={theme}>
        {children}
      </ChakraProvider>
    </>
  )
}
```

### 2.2 Theme Toggle Component

**File:** `frontend/src/components/ThemeToggle.tsx`

```tsx
'use client'

import { IconButton, useColorMode, useColorModeValue } from '@chakra-ui/react'
import { FiSun, FiMoon } from 'react-icons/fi'

export function ThemeToggle() {
  const { colorMode, toggleColorMode } = useColorMode()
  
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
```

### 2.3 Header Integration

**File:** `frontend/src/components/Header.tsx` (Update existing)

```tsx
// Add to imports
import { ThemeToggle } from './ThemeToggle'

// Add to header actions (after collection status)
<HStack spacing={4}>
  {/* Existing collection status */}
  <ThemeToggle />
</HStack>
```

### 2.4 Root Layout Update

**File:** `frontend/src/app/layout.tsx` (Update existing)

```tsx
import { ColorModeScript } from '@chakra-ui/react'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <ColorModeScript initialColorMode="system" />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
```

---

## 3. Component Updates Required

### 3.1 Cards and Containers

All card components need color mode support:

```tsx
// Example: Status cards in dashboard
<Box
  bg={useColorModeValue('white', 'gray.800')}
  borderColor={useColorModeValue('gray.200', 'gray.600')}
  shadow={useColorModeValue('sm', 'dark-lg')}
>
```

### 3.2 Modals and Overlays

```tsx
// Example: Collection modal
<Modal>
  <ModalOverlay bg={useColorModeValue('blackAlpha.300', 'blackAlpha.600')} />
  <ModalContent bg={useColorModeValue('white', 'gray.800')}>
```

### 3.3 Form Elements

```tsx
// Example: Input fields
<Input
  bg={useColorModeValue('white', 'gray.700')}
  borderColor={useColorModeValue('gray.300', 'gray.600')}
  _focus={{
    borderColor: useColorModeValue('blue.500', 'blue.300'),
    boxShadow: useColorModeValue('0 0 0 1px blue.500', '0 0 0 1px blue.300'),
  }}
/>
```

---

## 4. Implementation Checklist

### 4.1 Core Setup
- [ ] Update `provider.tsx` with theme configuration
- [ ] Create `ThemeToggle.tsx` component
- [ ] Add `ColorModeScript` to root layout
- [ ] Test system preference detection

### 4.2 Component Updates
- [ ] Update `Header.tsx` with theme toggle
- [ ] Update all card components (`page.tsx` dashboard)
- [ ] Update modal components (`CollectionModal.tsx`, `AddImagesModal.tsx`)
- [ ] Update form elements and inputs
- [ ] Update search page components
- [ ] Update logs page components

### 4.3 Testing & Polish
- [ ] Test toggle performance (≤ 100ms)
- [ ] Test system preference changes
- [ ] Test localStorage persistence
- [ ] Verify smooth transitions
- [ ] Test on different devices/browsers

---

**Implementation Priority:** High  
**Estimated Timeline:** 1-2 days  
**Dependencies:** None (can be implemented immediately)  
**Risk Level:** Low (well-established patterns with Chakra UI)

Ready to implement! This will significantly improve the user experience. 🌙✨ 