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
  StatHelpText,
  useColorModeValue,
  Flex,
  Badge,
  Divider,
  Progress,
  Heading,
  Container
} from '@chakra-ui/react';
import { FiSearch, FiUpload, FiFolder, FiEye, FiZap, FiShield, FiDatabase, FiLayers } from 'react-icons/fi';
import { Header } from '@/components/Header';
import { CollectionModal } from '@/components/CollectionModal';
import { AddImagesModal } from '@/components/AddImagesModal';
import { CollectionStats } from '@/components/CollectionStats';
import { useStore } from '@/store/useStore';
import { ping } from '@/lib/api';
import { HomeDashboard } from '@/components/HomeDashboard';

export default function Home() {
  return <HomeContent />;
}

function HomeContent() {
  const router = useRouter();
  const { collection } = useStore();
  const [backendStatus, setBackendStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [setupStep, setSetupStep] = useState(1);
  const [mounted, setMounted] = useState(false);
  
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
    setMounted(true);
  }, []);

  // Dark mode aware colors - ALL at top level to avoid Hook rule violations
  const sidebarBg = useColorModeValue('white', 'gray.800');
  const textColor = useColorModeValue('gray.800', 'white');
  const mutedTextColor = useColorModeValue('gray.600', 'gray.300');
  const cardBgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const brandGradient = useColorModeValue(
    'linear(to-r, blue.500, purple.600)',
    'linear(to-r, blue.300, purple.400)'
  );
  const progressBg = useColorModeValue('gray.100', 'gray.700');

  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        await ping();
        setBackendStatus('ok');
      } catch (error) {
        console.error('Backend health check failed:', error);
        setBackendStatus('error');
      }
    };

    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Determine setup progress
  useEffect(() => {
    if (backendStatus === 'ok' && collection) {
      setSetupStep(3); // Ready to use
    } else if (backendStatus === 'ok') {
      setSetupStep(2); // Need collection
    } else {
      setSetupStep(1); // Backend issues
    }
  }, [backendStatus, collection]);

  const getSetupProgress = () => {
    switch (setupStep) {
      case 1: return { progress: 0, label: 'Connecting to services...', color: 'red' };
      case 2: return { progress: 50, label: 'Select or create a collection', color: 'yellow' };
      case 3: return { progress: 100, label: 'Ready to search!', color: 'green' };
      default: return { progress: 0, label: 'Initializing...', color: 'gray' };
    }
  };

  const setupProgress = getSetupProgress();

  const quickActions = [
    {
      title: 'Search Images',
      description: 'Find images using AI-powered semantic search',
      icon: FiSearch,
      color: 'blue',
      action: () => router.push('/search'),
      disabled: setupStep < 3,
      featured: true
    },
    {
      title: 'Latent Space',
      description: 'Visualize and explore your collection in 2D embedding space',
      icon: FiZap,
      color: 'purple',
      action: () => router.push('/latent-space'),
      disabled: setupStep < 3,
      featured: true
    },
    {
      title: 'Add Images',
      description: 'Upload and process new images for your collection',
      icon: FiUpload,
      color: 'green',
      action: onAddImagesModalOpen,
      disabled: setupStep < 3,
      featured: true
    },
    {
      title: 'View Activity',
      description: 'Monitor system activity and processing jobs',
      icon: FiEye,
      color: 'orange',
      action: () => router.push('/logs'),
      disabled: false,
      featured: false
    },
    {
      title: 'Duplicate Management',
      description: 'Find and archive duplicate images',
      icon: FiLayers,
      color: 'red',
      action: () => router.push('/duplicates'),
      disabled: setupStep < 3,
      featured: false
    },
    {
      title: 'Manage Collections',
      description: 'Create or switch between collections',
      icon: FiFolder,
      color: 'purple',
      action: onCollectionModalOpen,
      disabled: false,
      featured: setupStep < 3
    }
  ];

  const featuredActions = quickActions.filter(action => action.featured);
  const otherActions = quickActions.filter(action => !action.featured);

  if (!mounted) {
    return null; // or a loading spinner
  }

  return (
    <Box minH="100vh">
      <Header />
      
      <Flex>
        {/* Sidebar */}
        <Box
          w="320px"
          bg={sidebarBg}
          borderRight="1px"
          borderColor={borderColor}
          h="calc(100vh - 80px)"
          p={6}
          overflow="auto"
        >
          <VStack spacing={6} align="stretch">
            {/* Setup Progress */}
            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb={3} color={textColor}>
                Setup Progress
              </Text>
              <VStack spacing={3} align="stretch">
                <Progress 
                  value={setupProgress.progress} 
                  colorScheme={setupProgress.color}
                  size="sm"
                  bg={progressBg}
                />
                <Text fontSize="sm" color={mutedTextColor}>
                  {setupProgress.label}
                </Text>
              </VStack>
            </Box>

            <Divider />

            {/* System Status */}
            <Box>
              <Text fontSize="sm" fontWeight="semibold" mb={3} color={textColor}>
                System Status
              </Text>
              <VStack spacing={3} align="stretch">
                <Card size="sm" bg={cardBgColor}>
                  <CardBody>
                    <Stat size="sm">
                      <StatLabel color={mutedTextColor}>Backend Services</StatLabel>
                      <StatNumber color={backendStatus === 'ok' ? 'green.500' : 'red.500'}>
                        {backendStatus === 'loading' ? 'Checking...' : 
                         backendStatus === 'ok' ? 'Online' : 'Offline'}
                      </StatNumber>
                      <StatHelpText color={mutedTextColor}>
                        {backendStatus === 'ok' ? 'All services running' : 'Services unavailable'}
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>

                <Card size="sm" bg={cardBgColor}>
                  <CardBody>
                    <Stat size="sm">
                      <StatLabel color={mutedTextColor}>Active Collection</StatLabel>
                      <StatNumber color={collection ? 'blue.500' : 'gray.400'}>
                        {collection || 'None Selected'}
                      </StatNumber>
                      <StatHelpText color={mutedTextColor}>
                        {collection ? 'Ready for operations' : 'Select a collection'}
                      </StatHelpText>
                    </Stat>
                  </CardBody>
                </Card>
              </VStack>
            </Box>

            {/* Collection Statistics */}
            {setupStep === 3 && (
              <>
                <Divider />
                <Box>
                  <Text fontSize="sm" fontWeight="semibold" mb={3} color={textColor}>
                    Collection Details
                  </Text>
                  <CollectionStats />
                </Box>
              </>
            )}

            {/* Quick Setup Actions */}
            {setupStep < 3 && (
              <>
                <Divider />
                <Box>
                  <Text fontSize="sm" fontWeight="semibold" mb={3} color={textColor}>
                    Next Steps
                  </Text>
                  <VStack spacing={2} align="stretch">
                    {setupStep === 1 && (
                      <Alert status="error" size="sm">
                        <AlertIcon />
                        <Text fontSize="xs">Backend services unavailable</Text>
                      </Alert>
                    )}
                    {setupStep === 2 && (
                      <Button
                        size="sm"
                        colorScheme="blue"
                        onClick={onCollectionModalOpen}
                        leftIcon={<Icon as={FiFolder} />}
                      >
                        Select Collection
                      </Button>
                    )}
                  </VStack>
                </Box>
              </>
            )}
          </VStack>
        </Box>

        {/* Main Content */}
        <Box flex="1" p={8}>
          <Container maxW="4xl">
            <VStack spacing={8} align="stretch">
              {/* Hero Section */}
              <Box textAlign="center">
                <VStack spacing={4}>
                  <HStack spacing={3}>
                    <Icon as={FiZap} boxSize={10} color="blue.500" />
                    <Heading 
                      size="2xl" 
                      bgGradient={brandGradient}
                      bgClip="text"
                      fontWeight="bold"
                    >
                      Pixel Detective
                    </Heading>
                  </HStack>
                  <Text fontSize="xl" color={mutedTextColor} maxW="2xl">
                    Your AI-powered image search and management platform. 
                    Find any image using natural language descriptions.
                  </Text>
                  
                  {setupStep === 3 && (
                    <Badge colorScheme="green" size="lg" px={3} py={1}>
                      🎉 Ready to Search!
                    </Badge>
                  )}
                </VStack>
              </Box>

              {/* Featured Actions */}
              {setupStep >= 3 && (
                <Box>
                  <Text fontSize="xl" fontWeight="bold" mb={6} color={textColor}>
                    Start Exploring
                  </Text>
                  
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    {featuredActions.map((action, index) => (
                      <Card 
                        key={index} 
                        cursor={action.disabled ? 'not-allowed' : 'pointer'}
                        opacity={action.disabled ? 0.6 : 1}
                        _hover={action.disabled ? {} : { 
                          shadow: 'xl', 
                          transform: 'translateY(-4px)',
                          borderColor: `${action.color}.500`
                        }}
                        transition="all 0.3s"
                        onClick={action.disabled ? undefined : action.action}
                        bg={cardBgColor}
                        borderWidth="2px"
                        borderColor="transparent"
                        size="lg"
                      >
                        <CardHeader>
                          <HStack>
                            <Icon 
                              as={action.icon} 
                              boxSize={8} 
                              color={`${action.color}.500`} 
                            />
                            <VStack align="start" spacing={1} flex="1">
                              <Text fontWeight="bold" fontSize="lg" color={textColor}>
                                {action.title}
                              </Text>
                              <Text fontSize="sm" color={mutedTextColor}>
                                {action.description}
                              </Text>
                            </VStack>
                          </HStack>
                        </CardHeader>
                      </Card>
                    ))}
                  </SimpleGrid>
                </Box>
              )}

              {/* Setup Guidance */}
              {setupStep < 3 && (
                <Box>
                  <Text fontSize="xl" fontWeight="bold" mb={6} color={textColor}>
                    Getting Started
                  </Text>
                  
                  <Card bg={cardBgColor} p={6}>
                    <VStack spacing={4} align="start">
                      <HStack>
                        <Icon as={FiShield} color="blue.500" boxSize={6} />
                        <Text fontWeight="semibold" color={textColor}>
                          Set up your first collection
                        </Text>
                      </HStack>
                      <Text color={mutedTextColor}>
                        Collections help organize your images. Create one to get started 
                        with searching and managing your image library.
                      </Text>
                      <Button
                        colorScheme="blue"
                        onClick={onCollectionModalOpen}
                        leftIcon={<Icon as={FiDatabase} />}
                        isDisabled={backendStatus !== 'ok'}
                      >
                        {backendStatus !== 'ok' ? 'Waiting for Backend...' : 'Create Collection'}
                      </Button>
                    </VStack>
                  </Card>
                </Box>
              )}

              {/* Other Actions */}
              <Box>
                <Text fontSize="lg" fontWeight="semibold" mb={4} color={textColor}>
                  Additional Tools
                </Text>
                
                <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
                  {otherActions.map((action, index) => (
                    <Card 
                      key={index} 
                      cursor={action.disabled ? 'not-allowed' : 'pointer'}
                      opacity={action.disabled ? 0.6 : 1}
                      _hover={action.disabled ? {} : { shadow: 'md', transform: 'translateY(-2px)' }}
                      transition="all 0.2s"
                      onClick={action.disabled ? undefined : action.action}
                      bg={cardBgColor}
                      size="sm"
                    >
                      <CardBody textAlign="center">
                        <VStack spacing={2}>
                          <Icon 
                            as={action.icon} 
                            boxSize={6} 
                            color={`${action.color}.500`} 
                          />
                          <Text fontWeight="semibold" fontSize="sm" color={textColor}>
                            {action.title}
                          </Text>
                        </VStack>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
              </Box>
            </VStack>
          </Container>
        </Box>
      </Flex>

      {/* Modals */}
      <CollectionModal isOpen={isCollectionModalOpen} onClose={onCollectionModalClose} />
      <AddImagesModal isOpen={isAddImagesModalOpen} onClose={onAddImagesModalClose} />
    </Box>
  );
}
