import React from 'react';
import {
  Box,
  VStack,
  Text,
  Heading,
  List,
  ListItem,
  Badge,
  useColorModeValue,
  Progress,
} from '@chakra-ui/react';

function TaskList({ tasks }) {
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'failed':
        return 'red';
      case 'running':
        return 'blue';
      default:
        return 'gray';
    }
  };

  return (
    <Box
      p={6}
      bg={bgColor}
      borderRadius="lg"
      boxShadow="sm"
      border="1px"
      borderColor={borderColor}
    >
      <VStack spacing={4} align="stretch">
        <Heading size="md">Active Tasks</Heading>
        <List spacing={3}>
          {tasks.map((task) => (
            <ListItem
              key={task.id}
              p={4}
              bg="gray.50"
              borderRadius="md"
              border="1px"
              borderColor="gray.200"
            >
              <VStack align="stretch" spacing={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Text fontWeight="bold" fontSize="sm">
                    Task ID: {task.id}
                  </Text>
                  <Badge colorScheme={getStatusColor(task.status)}>
                    {task.status}
                  </Badge>
                </Box>
                
                <Text fontSize="sm" color="gray.600">
                  Query: {task.query}
                </Text>

                {task.status === 'running' && (
                  <Progress size="sm" isIndeterminate colorScheme="blue" />
                )}

                {task.error && (
                  <Text color="red.500" fontSize="sm">
                    Error: {task.error}
                  </Text>
                )}
              </VStack>
            </ListItem>
          ))}
        </List>
      </VStack>
    </Box>
  );
}

export default TaskList; 