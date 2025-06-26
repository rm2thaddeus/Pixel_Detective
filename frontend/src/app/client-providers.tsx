'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { api } from '@/lib/api';

function CollectionSyncProvider({ children }: { children: React.ReactNode }) {
  const { collection } = useStore();
  
  useEffect(() => {
    console.log(`🔄 CollectionSyncProvider: collection state changed to: ${collection}`);
    
    if (collection) {
      console.log(`📡 Syncing collection '${collection}' with backend...`);
      // Sync the collection with the backend
      api.post('/api/v1/collections/select', {
        collection_name: collection
      }).then(response => {
        console.log(`✅ Collection sync successful:`, response.data);
      }).catch(error => {
        console.warn('❌ Failed to sync collection with backend:', error);
      });
    }
  }, [collection]);
  
  return <>{children}</>;
}

export function ClientProviders({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <CollectionSyncProvider>
        {children}
      </CollectionSyncProvider>
    </QueryClientProvider>
  );
} 