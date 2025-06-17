'use client';

import { useState, useEffect, type ReactNode } from 'react';

interface ClientOnlyProps {
  children: ReactNode;
}

/**
 * A wrapper component that ensures its children are only rendered on the client side.
 * This is crucial for resolving Next.js hydration errors that occur when server-rendered
 * HTML does not match the client-rendered HTML, often due to dynamic values like
 * color mode, window dimensions, or locale-specific formatting.
 */
export function ClientOnly({ children }: ClientOnlyProps) {
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  if (!hasMounted) {
    return null;
  }

  return <>{children}</>;
} 