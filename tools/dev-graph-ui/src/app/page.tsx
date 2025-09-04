'use client';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to dev-graph page
    router.push('/dev-graph');
  }, [router]);

  return null;
}