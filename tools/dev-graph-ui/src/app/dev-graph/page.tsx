'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DevGraphPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the new welcome dashboard
    router.push('/dev-graph/welcome');
  }, [router]);

  return null;
}
