'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DevGraphPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the beautiful complex dev-graph page
    router.push('/dev-graph/complex');
  }, [router]);

  return null;
}
