import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Textarea,
  VStack,
  useColorModeValue,
} from '@chakra-ui/react';

function QueryForm({ onSubmit, isLoading }) {
  const [query, setQuery] = useState('');
  const bgColor = useColorModeValue('white', 'gray.700');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
    }
  };

  return (
    <Box
      as="form"
      onSubmit={handleSubmit}
      p={6}
      bg={bgColor}
      borderRadius="lg"
      boxShadow="sm"
    >
      <VStack spacing={4}>
        <FormControl>
          <FormLabel>Enter your query</FormLabel>
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., calculate 2+2 or search for today's weather"
            size="lg"
            rows={4}
            isRequired
          />
        </FormControl>

        <Button
          type="submit"
          colorScheme="teal"
          size="lg"
          isLoading={isLoading}
          loadingText="Processing..."
          width="100%"
        >
          Submit Query
        </Button>
      </VStack>
    </Box>
  );
}

export default QueryForm; 