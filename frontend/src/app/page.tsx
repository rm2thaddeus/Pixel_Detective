'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  VStack,
  HStack,
  Text,
  Button,
  SimpleGrid,
  Card,
  CardBody,
  CardHeader,
  Icon,
  useDisclosure,
  Alert,
  AlertIcon,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText
} from '@chakra-ui/react';
import { FiDatabase, FiPlus, FiSearch, FiActivity } from 'react-icons/fi';
import { Header } from '@/components/Header';
import { CollectionModal } from '@/components/CollectionModal';
import { AddImagesModal } from '@/components/AddImagesModal';
import { useStore } from '@/store/useStore';
import { ping } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const { collection } = useStore();
  const [backendStatus, setBackendStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  
  const {
    isOpen: isCollectionModalOpen,
    onOpen: onCollectionModalOpen,
    onClose: onCollectionModalClose,
  } = useDisclosure();
  
  const {
    isOpen: isAddImagesModalOpen,
    onOpen: onAddImagesModalOpen,
    onClose: onAddImagesModalClose,
  } = useDisclosure();

  useEffect(() => {
    const checkBackend = async () => {
      try {
        await ping();
        setBackendStatus('ok');
      } catch {
        setBackendStatus('error');
      }
    };
    
    checkBackend();
  }, []);

  const quickActions = [
    {
      title: 'Manage Collections',
      description: 'Create, select, and manage your image collections',
      icon: FiDatabase,
      color: 'blue',
      action: onCollectionModalOpen,
      disabled: backendStatus !== 'ok'
    },
    {
      title: 'Add Images',
      description: 'Ingest images from a folder into your collection',
      icon: FiPlus,
      color: 'green',
      action: onAddImagesModalOpen,
      disabled: backendStatus !== 'ok' || !collection
    },
    {
      title: 'Search Images',
      description: 'Find images using natural language descriptions',
      icon: FiSearch,
      color: 'purple',
      action: () => router.push('/search'),
      disabled: backendStatus !== 'ok' || !collection
    }
  ];

  return (
    <Box>
      <Header />
      
      <Box p={8} maxW="6xl" mx="auto">
        <VStack spacing={8} align="stretch">
          {/* Welcome Section */}
          <Box textAlign="center">
            <Text fontSize="4xl" fontWeight="bold" mb={4}>
              Welcome to Vibe Coding
            </Text>
            <Text fontSize="xl" color="gray.600" mb={6}>
              Your AI-powered image search and management platform
            </Text>
            
            {backendStatus === 'error' && (
              <Alert status="error" mb={6}>
                <AlertIcon />
                Backend services are not available. Please check that the services are running.
              </Alert>
            )}
          </Box>

          {/* Status Overview */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
            <Card>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Backend Status</StatLabel>
                  <StatNumber color={backendStatus === 'ok' ? 'green.500' : 'red.500'}>
                    {backendStatus === 'loading' ? 'Checking...' : 
                     backendStatus === 'ok' ? 'Online' : 'Offline'}
                  </StatNumber>
                  <StatHelpText>
                    {backendStatus === 'ok' ? 'All services running' : 'Services unavailable'}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>Active Collection</StatLabel>
                  <StatNumber color={collection ? 'blue.500' : 'gray.400'}>
                    {collection || 'None'}
                  </StatNumber>
                  <StatHelpText>
                    {collection ? 'Ready for operations' : 'Select a collection'}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody textAlign="center">
                <Stat>
                  <StatLabel>System Status</StatLabel>
                  <StatNumber color={backendStatus === 'ok' && collection ? 'green.500' : 'orange.500'}>
                    {backendStatus === 'ok' && collection ? 'Ready' : 'Setup Required'}
                  </StatNumber>
                  <StatHelpText>
                    {backendStatus === 'ok' && collection ? 'All systems go' : 'Complete setup'}
                  </StatHelpText>
                </Stat>
              </CardBody>
            </Card>
          </SimpleGrid>

          {/* Quick Actions */}
          <Box>
            <Text fontSize="2xl" fontWeight="bold" mb={6} textAlign="center">
              Quick Actions
            </Text>
            
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
              {quickActions.map((action, index) => (
                <Card 
                  key={index} 
                  cursor={action.disabled ? 'not-allowed' : 'pointer'}
                  opacity={action.disabled ? 0.6 : 1}
                  _hover={action.disabled ? {} : { shadow: 'lg', transform: 'translateY(-2px)' }}
                  transition="all 0.2s"
                  onClick={action.disabled ? undefined : action.action}
                >
                  <CardHeader textAlign="center">
                    <Icon 
                      as={action.icon} 
                      boxSize={12} 
                      color={`${action.color}.500`} 
                      mb={4}
                    />
                    <Text fontSize="xl" fontWeight="semibold">
                      {action.title}
                    </Text>
                  </CardHeader>
                  <CardBody pt={0} textAlign="center">
                    <Text color="gray.600" mb={4}>
                      {action.description}
                    </Text>
                    <Button
                      colorScheme={action.color}
                      size="sm"
                      isDisabled={action.disabled}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!action.disabled) action.action();
                      }}
                    >
                      {action.title}
                    </Button>
                  </CardBody>
                </Card>
              ))}
            </SimpleGrid>
          </Box>

          {/* Getting Started Guide */}
          {(!collection || backendStatus !== 'ok') && (
            <Card bg="blue.50" borderColor="blue.200">
              <CardHeader>
                <HStack>
                  <Icon as={FiActivity} color="blue.500" />
                  <Text fontSize="lg" fontWeight="semibold" color="blue.700">
                    Getting Started
                  </Text>
                </HStack>
              </CardHeader>
              <CardBody pt={0}>
                <VStack align="start" spacing={2} color="blue.700">
                  {backendStatus !== 'ok' && (
                    <Text>• ⚠️ Start the backend services first</Text>
                  )}
                  {backendStatus === 'ok' && !collection && (
                    <>
                      <Text>• ✅ Backend is running</Text>
                      <Text>• 📁 Create or select a collection to get started</Text>
                    </>
                  )}
                  {backendStatus === 'ok' && collection && (
                    <>
                      <Text>• ✅ Backend is running</Text>
                      <Text>• ✅ Collection &quot;{collection}&quot; is selected</Text>
                      <Text>• 🚀 You&apos;re ready to add images and search!</Text>
                    </>
                  )}
                </VStack>
              </CardBody>
            </Card>
          )}
        </VStack>
      </Box>

      {/* Modals */}
      <CollectionModal 
        isOpen={isCollectionModalOpen} 
        onClose={onCollectionModalClose} 
      />
      <AddImagesModal 
        isOpen={isAddImagesModalOpen} 
        onClose={onAddImagesModalClose} 
      />
    </Box>
  );
}
