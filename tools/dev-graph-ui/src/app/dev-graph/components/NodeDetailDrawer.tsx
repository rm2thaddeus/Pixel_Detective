'use client';

import { useEffect, useMemo, useState } from 'react';
import { Drawer, DrawerBody, DrawerCloseButton, DrawerContent, DrawerHeader, DrawerOverlay, Heading, Text, VStack, Badge, Divider, Spinner, Box } from '@chakra-ui/react';

const DEV_GRAPH_API_URL = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';

export function NodeDetailDrawer({ isOpen, onClose, node }: { isOpen: boolean; onClose: () => void; node: any | null }) {
  const entries = node ? Object.entries(node).filter(([k]) => k !== 'id') : [];

  const isRequirement = useMemo(() => {
    if (!node) return false;
    return node?.type === 'Requirement' || (typeof node?.id === 'string' && /^(FR|NFR)-\d+/.test(node.id));
  }, [node]);

  const isFile = useMemo(() => {
    if (!node) return false;
    return !!node?.path || node?.type === 'File';
  }, [node]);

  const [events, setEvents] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!node || !isOpen) return;
      setLoading(true);
      setError(null);
      setEvents(null);
      try {
        if (isRequirement) {
          const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/requirement/${encodeURIComponent(node.id)}`);
          if (!res.ok) throw new Error('Failed to load requirement evolution');
          const data = await res.json();
          if (!cancelled) setEvents(data);
        } else if (isFile) {
          const p = node.path || node.id; // fallback if node.id is file path id
          const res = await fetch(`${DEV_GRAPH_API_URL}/api/v1/dev-graph/evolution/file?path=${encodeURIComponent(p)}`);
          if (!res.ok) throw new Error('Failed to load file evolution');
          const data = await res.json();
          if (!cancelled) setEvents(data);
        } else {
          if (!cancelled) setEvents([]);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load evolution');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [node, isRequirement, isFile, isOpen]);

  return (
    <Drawer isOpen={isOpen} placement="right" onClose={onClose} size="md">
      <DrawerOverlay />
      <DrawerContent>
        <DrawerCloseButton />
        <DrawerHeader>
          <Heading size="md">{node?.id}</Heading>
          {node?.type && <Badge ml={2}>{node.type}</Badge>}
        </DrawerHeader>
        <DrawerBody>
          <VStack align="stretch" spacing={3}>
            {entries.map(([k, v]) => (
              <Text key={k} fontSize="sm"><b>{k}:</b> {typeof v === 'object' ? JSON.stringify(v) : String(v)}</Text>
            ))}
            <Divider />
            <Heading size="sm">Evolution Timeline</Heading>
            {loading && (
              <Box display="flex" alignItems="center" gap={2}><Spinner size="sm" /> Loading…</Box>
            )}
            {error && (
              <Text fontSize="sm" color="red.500">{error}</Text>
            )}
            {!loading && !error && (
              <VStack align="stretch" spacing={2}>
                {(events || []).map((e: any, idx: number) => (
                  <Box key={`${e.type}-${idx}`}>
                    <Text fontSize="sm" fontWeight="semibold">{e.title || e.type}</Text>
                    {e.timestamp && <Text fontSize="xs" color="gray.600">{new Date(e.timestamp).toLocaleString()}</Text>}
                    {e.commit && <Text fontSize="xs" color="gray.600">Commit: {e.commit}</Text>}
                  </Box>
                ))}
                {Array.isArray(events) && events.length === 0 && (
                  <Text fontSize="sm" color="gray.600">No evolution events</Text>
                )}
              </VStack>
            )}
          </VStack>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}

export default NodeDetailDrawer;


