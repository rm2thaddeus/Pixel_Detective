'use client';

import { HStack, Input, Button } from '@chakra-ui/react';
import { useState } from 'react';

export function SearchBar({ onSearch }: { onSearch: (q: string) => void }) {
  const [q, setQ] = useState('');
  return (
    <HStack>
      <Input placeholder="Search nodes..." value={q} onChange={(e) => setQ(e.target.value)} />
      <Button onClick={() => onSearch(q)} colorScheme="blue">Search</Button>
    </HStack>
  );
}

export default SearchBar;


