import React from 'react';
import {
  Box,
  useColorModeValue,
} from '@chakra-ui/react';

function ResultDisplay({ result }) {
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  if (!result) return null;

  const cleanContent = (text) => {
    if (!text) return '';
    // Remove any URLs in parentheses
    text = text.replace(/\(https?:\/\/[^)]+\)/g, '');
    // Remove any standalone URLs
    text = text.replace(/https?:\/\/\S+/g, '');
    // Remove any citation numbers [1], [2], etc.
    text = text.replace(/\[\d+\]/g, '');
    // Remove extra whitespace and newlines
    text = text.replace(/\s+/g, ' ').trim();
    return text;
  };

  const extractContent = (response) => {
    try {
      if (!response) return null;

      // If response is a string, try to parse it as JSON
      let data = typeof response === 'string' ? JSON.parse(response) : response;

      // If data is still a string (parsing failed), try to extract content using regex
      if (typeof data === 'string') {
        const contentMatch = data.match(/content':\s*'([^']+)'/);
        if (contentMatch) {
          return cleanContent(contentMatch[1]);
        }
        return cleanContent(data);
      }

      // Handle structured response
      if (data.results && Array.isArray(data.results)) {
        // Get content from the first result
        const content = data.results[0]?.content;
        if (content) {
          return cleanContent(content);
        }
      }

      // If there's a direct answer field
      if (data.answer) {
        return cleanContent(data.answer);
      }

      return 'No relevant information found.';
    } catch (e) {
      console.error('Error processing response:', e);
      // If the response is a string but not valid JSON, try to clean it directly
      if (typeof response === 'string') {
        return cleanContent(response);
      }
      return 'Error processing the response.';
    }
  };

  const finalContent = extractContent(result.response);

  return (
    <Box
      p={6}
      bg={bgColor}
      borderRadius="lg"
      boxShadow="sm"
      border="1px"
      borderColor={borderColor}
      fontSize="lg"
      whiteSpace="pre-wrap"
    >
      {finalContent}
    </Box>
  );
}

export default ResultDisplay; 