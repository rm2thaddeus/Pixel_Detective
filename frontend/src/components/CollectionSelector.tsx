import {
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
  Spinner,
  HStack,
  Icon,
  Badge,
  Text,
} from '@chakra-ui/react';
import { FiChevronDown, FiFolder } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getCollections, selectCollection } from '@/lib/api';
import { useStore } from '@/store/useStore';

export function CollectionSelector() {
  const activeCollection = useStore((s) => s.collection);
  const setActive = useStore((s) => s.setCollection);
  const queryClient = useQueryClient();

  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: getCollections,
  });

  const mutation = useMutation({
    mutationFn: selectCollection,
    onSuccess: (_, selectedName) => {
      setActive(selectedName);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
    },
  });

  return (
    <Menu>
      <MenuButton as={Button} rightIcon={<Icon as={FiChevronDown} />} variant="outline" size="sm">
        <HStack spacing={2}>
          <Icon as={FiFolder} />
          <Text>{activeCollection || 'No Collection'}</Text>
        </HStack>
      </MenuButton>
      <MenuList minW="220px">
        {isLoading && (
          <HStack p={3} justifyContent="center">
            <Spinner size="sm" />
          </HStack>
        )}
        {collections?.map((name) => (
          <MenuItem
            key={name}
            onClick={() => mutation.mutate(name)}
            closeOnSelect
          >
            <HStack w="full" justifyContent="space-between">
              <Text>{name}</Text>
              {name === activeCollection && <Badge colorScheme="green">active</Badge>}
            </HStack>
          </MenuItem>
        ))}
      </MenuList>
    </Menu>
  );
} 