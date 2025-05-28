import os
import json
import re
import logging
from typing import Dict, List, Any

from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate

# Direct import from exceptions module
from exceptions import ReflectionError, JSONParsingError

# Initialize logger for this module
logger = logging.getLogger("agents")

REFLECT_PROMPT = """You are a ReflectorAgent responsible for evaluating task execution results and suggesting refinements.

Context:
Original Query: {query}
Executed Tasks: {tasks}
Task Results: {results}

Your job is to:
1. Evaluate if the tasks were executed successfully (check status fields in results).
2. Determine if the results (even if some tasks failed) collectively satisfy the original query.
3. If not complete or successful, suggest task refinements (modify, add, remove) or new tasks.
   - For failed tasks, you might suggest retrying with modifications or removing them if not critical.
   - Ensure 'details' for refinements are valid JSON strings if they represent new task structures or modifications.

Examples of refinements:
- Modify task parameters for better accuracy: {{"action": "modify", "task_id": 1, "details": "{{\\"description\\": \\"Search Tokyo average temperature in Celsius\\"}}"}}
- Add new tasks to gather missing information: {{"action": "add", "task_id": null, "details": "{{\\"id\\": 4, \\"description\\": \\"Convert NY temperature to Celsius\\", \\"tool\\": \\"calculator\\"}}"}}
- Remove redundant or failed tasks: {{"action": "remove", "task_id": 2, "details": "Task failed repeatedly and is not critical"}}

Return a JSON object with:
{{
    "success": true/false,  // Overall success in achieving the query goal so far
    "complete": true/false, // Is the original query fully addressed?
    "feedback": "Detailed feedback about results and progress towards the query.",
    "refinements": [
        {{
            "action": "modify/add/remove", // Action to take
            "task_id": task_id_or_null,   // ID of the task to modify/remove, or null for new tasks
            "details": "Specific changes (JSON string for add/modify task) or reason for removal (string)"
        }}
    ]
}}

If all tasks succeeded and the query seems complete, set success and complete to true with positive feedback.
If errors occurred or more work is needed, set success/complete to false and provide refinements.
If no refinements can be suggested for a failed state, return empty refinements list.
Evaluate the results and provide your assessment:"""

class ReflectorAgent:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logger.error("GROQ_API_KEY environment variable is not set for ReflectorAgent")
            raise EnvironmentError("GROQ_API_KEY environment variable is not set")

        logger.info(f"Initializing ReflectorAgent with model: {model_name}")
        try:
            self.llm = ChatGroq(
                model_name=model_name,
                temperature=temperature,
                groq_api_key=groq_api_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq for ReflectorAgent: {e}", exc_info=True)
            raise ReflectionError(f"Failed to initialize ChatGroq for ReflectorAgent: {e}") from e
        self.prompt = ChatPromptTemplate.from_template(REFLECT_PROMPT)

    def _extract_json(self, content: str) -> str:
        logger.debug(f"Reflector: Attempting to extract JSON from content: {content[:500]}...")
        stripped_content = content.strip()
        # Regex to find content within ```json ... ``` or ``` ... ``` or a standalone JSON object
        match = re.search(r"```(?:json)?\s*({[\s\S]*?})\s*```|({[\s\S]*})", stripped_content, re.IGNORECASE | re.DOTALL)
        if match:
            # Group 2 will capture standalone JSON, Group 1 will capture JSON in backticks.
            # Prefer Group 1 if available (JSON in backticks), else use Group 2.
            extracted_block = match.group(1) if match.group(1) else match.group(2)
            if extracted_block:
                logger.debug(f"Reflector: Found JSON: {extracted_block[:500]}...")
                # Basic normalization (e.g. remove trailing commas before closing brace)
                normalized_block = re.sub(r',\s*([}])', r'\\1', extracted_block.strip())
                return normalized_block
        logger.warning(f"Reflector: Could not find valid JSON object in LLM response: {content[:500]}...")
        return stripped_content # Fallback, hoping json.loads can handle or give good error

    def evaluate_results(self, query: str, tasks: List[Dict[str, Any]], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info("Reflector: Evaluating task execution results.")
        logger.debug(f"Query: {query}")
        logger.debug(f"Tasks: {tasks}")
        logger.debug(f"Results: {results}")

        json_content_for_error = ""
        try:
            # Format inputs, ensuring lists are properly represented for the prompt
            formatted_tasks = json.dumps(tasks, indent=2)
            formatted_results = json.dumps(results, indent=2)

            messages = self.prompt.format_messages(
                query=query,
                tasks=formatted_tasks,
                results=formatted_results
            )
            
            logger.debug("Reflector: Sending request to Groq API for reflection.")
            response = self.llm.invoke(messages)
            content = response.content.strip() if response and hasattr(response, 'content') else None

            if not content:
                logger.error("Reflector: Empty response content from LLM during reflection.")
                raise ReflectionError("Empty response from LLM during reflection")
            
            logger.debug(f"Reflector: Raw LLM response for reflection: {content[:500]}...")
            json_content_for_error = content

            extracted_content = self._extract_json(content)
            json_content_for_error = extracted_content

            logger.debug(f"Reflector: Attempting to parse JSON for reflection: {extracted_content[:500]}...")
            try:
                reflection = json.loads(extracted_content)
            except json.JSONDecodeError as e:
                logger.error(f"Reflector: JSON decode error for content: '{extracted_content[:500]}...'. Error: {e}", exc_info=True)
                raise JSONParsingError(content=extracted_content, error=str(e)) from e
            
            # Validate reflection format
            required_fields = ["success", "complete", "feedback", "refinements"]
            if not all(field in reflection for field in required_fields):
                logger.error(f"Reflector: Reflection missing required fields. Got: {reflection.keys()}. Expected: {required_fields}")
                raise ReflectionError(f"Reflection object missing required fields. Expected {required_fields}, got {list(reflection.keys())}")
            if not isinstance(reflection.get("refinements"), list):
                 logger.error(f"Reflector: 'refinements' field is not a list. Got: {type(reflection.get('refinements'))}")
                 raise ReflectionError(f"'refinements' field must be a list, got {type(reflection.get('refinements'))}")

            logger.info(f"Reflector: Reflection successful. Feedback: {reflection.get('feedback')}")
            logger.debug(f"Reflection results: {json.dumps(reflection, indent=2)}")
            return reflection
            
        except JSONParsingError as e: # Already logged
            raise ReflectionError(f"Failed to parse reflection JSON: {e}") from e # Wrap for specific context
        except ReflectionError as e: # Catch specific reflection errors
            logger.error(f"ReflectionError occurred: {e}", exc_info=True)
            raise # Re-raise to be caught by main_workflow or API
        except Exception as e:
            logger.error(f"Reflector: Unexpected error during result evaluation: {e}", exc_info=True)
            error_message = f"Unexpected error during reflection: {e}. "
            if json_content_for_error:
                error_message += f"Problematic JSON content (approximate): {json_content_for_error[:200]}..."
            # Instead of returning a default, raise an exception so the workflow can handle it.
            raise ReflectionError(error_message) from e 