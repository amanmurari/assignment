import React, { useState } from 'react';
import {
  Box,
  Container,
  VStack,
  Heading,
  Text,
  useToast,
  ChakraProvider,
  extendTheme,
} from '@chakra-ui/react';
import QueryForm from './components/QueryForm';
import ResultDisplay from './components/ResultDisplay';
import { executeQuery } from './api';

const theme = extendTheme({
  styles: {
    global: {
      body: {
        bg: 'gray.50',
      },
    },
  },
  components: {
    Button: {
      defaultProps: {
        colorScheme: 'teal',
      },
    },
  },
});

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleQuerySubmit = async (query) => {
    setLoading(true);
    try {
      const response = await executeQuery(query, false); // Always use synchronous execution
      setResult(response);
      toast({
        title: 'Success',
        description: 'Query processed successfully.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error.message || 'An error occurred while processing your query.',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <ChakraProvider theme={theme}>
      <Box minH="100vh" py={8}>
        <Container maxW="container.xl">
          <VStack spacing={8} align="stretch">
            <Box textAlign="center" mb={8}>
              <Heading size="2xl" mb={2}>Agentic Workflow</Heading>
              <Text fontSize="lg" color="gray.600">
                Intelligent task planning and execution using language models
              </Text>
            </Box>

            <QueryForm onSubmit={handleQuerySubmit} isLoading={loading} />
            
            {result && (
              <ResultDisplay result={result} />
            )}
          </VStack>
        </Container>
      </Box>
    </ChakraProvider>
  );
}

export default App; 