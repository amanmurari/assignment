import os
import json
import re
import logging
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate

# Direct import from exceptions module
from exceptions import PlanningError, JSONParsingError, TaskValidationError

# Initialize logger for this module
logger = logging.getLogger("agents")

PLAN_PROMPT = '''You are a PlanAgent that can ONLY use two specific tools. NO OTHER TOOLS ARE ALLOWED.

STRICT RULES:
1. You can ONLY use these exact tools:
   - "search": For ALL information gathering (web searches, news, weather, etc.)
   - "calculator": For mathematical calculations ONLY

2. If a search fails:
   - DO NOT suggest alternative tools
   - DO NOT try to use web scrapers or other tools
   - Simply use the "search" tool again with a modified query

Examples:

1. User Query: "Find the current Prime Minister of India"
[
  {{"id": 1, "description": "Search for current Prime Minister of India", "tool": "search"}}
]

2. User Query: "calculate 2+2"
[
  {{"id": 1, "description": "2+2", "tool": "calculator"}}
]

3. User Query: "what is today's weather"
[
  {{"id": 1, "description": "Search for current weather conditions", "tool": "search"}}
]

4. User Query: "check news about SpaceX"
[
  {{"id": 1, "description": "Search for latest SpaceX news", "tool": "search"}}
]

Current Query: {query}

REQUIREMENTS:
1. Return ONLY a JSON array of tasks
2. Each task MUST have exactly these fields:
   - "id": A number (1, 2, 3, etc.)
   - "description": What to search for or calculate
   - "tool": MUST be exactly "search" or "calculator" (no other values allowed)
3. DO NOT add any extra fields or parameters
4. DO NOT suggest alternative tools or methods
5. Use "search" for ALL information gathering needs

REMEMBER: If a task fails, the workflow will handle retries automatically. DO NOT try to implement your own retry logic or alternative tools.
'''

class PlannerAgent:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0):
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logger.error("GROQ_API_KEY environment variable is not set")
            raise EnvironmentError("GROQ_API_KEY environment variable is not set")
            
        logger.info(f"Initializing PlannerAgent with model: {model_name}")
        try:
            self.llm = ChatGroq(
                model_name=model_name,
                temperature=temperature,
                groq_api_key=groq_api_key
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGroq: {str(e)}", exc_info=True)
            raise PlanningError(f"Failed to initialize ChatGroq: {str(e)}") from e
            
        self.prompt = ChatPromptTemplate.from_template(PLAN_PROMPT)

    def _clean_calculator_expression(self, expr: str) -> str:
        """Clean and validate calculator expression."""
        logger.debug(f"Cleaning calculator expression: '{expr}'")
        allowed_chars = set("0123456789+-*/.() ")
        cleaned = ''.join(c for c in expr if c in allowed_chars)
        cleaned = cleaned.strip()
        logger.debug(f"Cleaned expression: '{cleaned}'")
        if not cleaned:
            logger.warning(f"Calculator expression '{expr}' became empty after cleaning.")
        return cleaned

    def _normalize_json(self, content: str) -> str:
        """Normalize JSON content by properly handling quotes and apostrophes."""
        logger.debug(f"Normalizing JSON content. Input: {content[:500]}...")
        
        try:
            # First try to parse it as-is
            json.loads(content)
            return content
        except json.JSONDecodeError:
            # If that fails, try to normalize it
            try:
                # Replace escaped quotes with temporary placeholder
                content = content.replace('\\"', '@@QUOTE@@')
                
                # Replace any remaining double quotes with escaped ones
                content = content.replace('"', '\\"')
                
                # Replace single quotes with double quotes
                content = content.replace("'", '"')
                
                # Restore originally escaped quotes
                content = content.replace('@@QUOTE@@', '\\"')
                
                # Ensure proper JSON structure
                if not content.strip().startswith('['):
                    content = f'[{content}]'
                
                # Validate the result
                json.loads(content)
                
                logger.debug(f"Normalized JSON content: {content[:500]}...")
                return content
            except Exception as e:
                logger.error(f"Failed to normalize JSON: {str(e)}")
                return content  # Return original content if normalization fails

    def _extract_json(self, content: str) -> str:
        logger.debug(f"Attempting to extract JSON from content: {content[:500]}...")
        
        # Try to find JSON array/object directly
        stripped_content = content.strip()
        if (stripped_content.startswith("[") and stripped_content.endswith("]")) or \
           (stripped_content.startswith("{") and stripped_content.endswith("}")):
            logger.debug("Found direct JSON array/object.")
            return self._normalize_json(stripped_content)
            
        # Look for JSON in code blocks
        # Regex to find content within ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\\s*([\s\S]*?)\\s*```", content, re.IGNORECASE)
        if match:
            extracted_block = match.group(1).strip()
            logger.debug(f"Found JSON in code block: {extracted_block[:500]}...")
            return self._normalize_json(extracted_block)
            
        logger.warning(f"Could not find valid JSON array or object in LLM response: {content[:500]}...")
        # Fallback to returning normalized content if no specific block is found,
        # hoping json.loads can handle it or provide a better error.
        return self._normalize_json(content)

    def _fix_task_format(self, task_data: Any) -> Dict[str, Any]:
        logger.debug(f"Attempting to fix task format for: {task_data} (type: {type(task_data)})")
        if not isinstance(task_data, dict):
            logger.error(f"Task item is not a dictionary. Received: {task_data}")
            raise TaskValidationError(task_data=str(task_data), message="Task item expected to be a dictionary")

        fixed_task = {}
        required_keys = ["id", "description", "tool"]

        # Copy required keys if they exist
        for key in required_keys:
            if key in task_data:
                fixed_task[key] = task_data[key]

        # Copy any additional keys
        for key, value in task_data.items():
            if key not in required_keys:
                fixed_task[key] = value

        logger.debug(f"Finished fixing task format. Result: {fixed_task}")
        return fixed_task

    def _validate_task(self, task: Dict[str, Any], task_index: int) -> bool:
        logger.debug(f"Validating task {task_index + 1}: {task}")
        required_fields = ["id", "description", "tool"]
        
        if not isinstance(task, dict):
            logger.error(f"Task {task_index + 1} is not a dict after fixing. This should not happen. Task: {task}")
            raise TaskValidationError(task_data=str(task), message=f"Task {task_index + 1} is not a dict after fixing.")

        missing_fields = [field for field in required_fields if field not in task]
        if missing_fields:
            logger.warning(f"Task {task_index + 1} missing required fields: {missing_fields}. Task data: {task}")
            return False
            
        # Validate field types
        if not isinstance(task.get("id"), (int, str)):
            logger.warning(f"Task {task_index + 1} id '{task.get('id')}' must be int or str, got {type(task.get('id'))}. Task data: {task}")
            return False
        if not isinstance(task.get("description"), str):
            logger.warning(f"Task {task_index + 1} description '{task.get('description')}' must be str, got {type(task.get('description'))}. Task data: {task}")
            return False
        if not isinstance(task.get("tool"), str):
            logger.warning(f"Task {task_index + 1} tool '{task.get('tool')}' must be str, got {type(task.get('tool'))}. Task data: {task}")
            return False
            
        # Validate tool name
        allowed_tools = ["search", "calculator"]
        if task.get("tool") not in allowed_tools:
            logger.warning(f"Task {task_index + 1} specifies an invalid tool: '{task.get('tool')}'. Allowed: {allowed_tools}. Task data: {task}")
            return False
            
        logger.info(f"Task {task_index + 1} validated successfully: {task}")
        return True

    def generate_plan(self, query: str) -> List[Dict[str, Any]]:
        logger.info(f"Generating plan for query: {query}")
        json_content_for_error = ""
        try:
            messages = self.prompt.format_messages(query=query)
            logger.debug("Sending request to Groq API...")
            response = self.llm.invoke(messages)
            logger.debug("Received response from Groq API.")
            
            content = response.content.strip() if response and hasattr(response, 'content') else None
            if not content:
                logger.error("Empty response content from LLM.")
                raise PlanningError("Empty response from LLM")
                
            logger.debug(f"Raw LLM response: {content[:500]}...")
            json_content_for_error = content

            extracted_content = self._extract_json(content)
            json_content_for_error = extracted_content
            
            logger.debug(f"Attempting to parse JSON: {extracted_content[:500]}...")
            try:
                parsed_tasks_data = json.loads(extracted_content)
                logger.debug(f"Successfully parsed JSON. Structure: {json.dumps(parsed_tasks_data, indent=2)}")
                logger.debug(f"First task (if exists): {parsed_tasks_data[0] if parsed_tasks_data else 'No tasks'}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for content: '{extracted_content[:500]}...'. Error: {e}", exc_info=True)
                raise JSONParsingError(content=extracted_content, error=str(e)) from e
            
            if not isinstance(parsed_tasks_data, list):
                logger.error(f"Parsed JSON is not a list of tasks, but {type(parsed_tasks_data)}. Data: {str(parsed_tasks_data)[:500]}")
                raise PlanningError(f"Expected list of tasks from LLM, got: {type(parsed_tasks_data)}")
            
            logger.info(f"Successfully parsed {len(parsed_tasks_data)} potential tasks from LLM.")
            
            valid_tasks = []
            for i, task_item_raw in enumerate(parsed_tasks_data):
                logger.debug(f"Processing task item {i + 1} (raw): {task_item_raw}")
                try:
                    logger.debug(f"Task item {i + 1} keys: {task_item_raw.keys() if isinstance(task_item_raw, dict) else 'Not a dict'}")
                    fixed_task_item = self._fix_task_format(task_item_raw)
                    logger.debug(f"Fixed task item {i + 1}: {fixed_task_item}")
                    
                    if self._validate_task(fixed_task_item, i):
                        if fixed_task_item["tool"] == "calculator":
                            cleaned_description = self._clean_calculator_expression(fixed_task_item["description"])
                            if not cleaned_description:
                                logger.warning(f"Task {i+1} (calculator) has an invalid/empty expression after cleaning: '{fixed_task_item['description']}'. Skipping.")
                                continue
                            fixed_task_item["description"] = cleaned_description
                        
                        valid_tasks.append(fixed_task_item)
                        logger.debug(f"Added valid task {i + 1}: {fixed_task_item}")
                    else:
                        logger.warning(f"Task item {i + 1} failed validation. Raw: {task_item_raw}, Fixed: {fixed_task_item}. Skipping.")
                
                except TaskValidationError as e:
                    logger.error(f"Task item {i + 1} ({task_item_raw}) is invalid and cannot be processed: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error processing task {i + 1}: {e}", exc_info=True)
                    raise

            if not valid_tasks and parsed_tasks_data:
                 logger.error("No valid tasks found after processing LLM response which contained potential tasks.")
                 raise PlanningError("No valid tasks derived from LLM response.")
            elif not parsed_tasks_data and not valid_tasks:
                 logger.info("LLM returned no tasks or unparsable content leading to no tasks.")

            logger.info(f"Generated {len(valid_tasks)} valid tasks: {json.dumps(valid_tasks, indent=2)}")
            return valid_tasks
            
        except JSONParsingError as e:
            raise
        except PlanningError as e:
            logger.error(f"PlanningError occurred: {e}", exc_info=True)
            raise
        except TaskValidationError as e:
            logger.error(f"TaskValidationError during plan generation: {e}", exc_info=True)
            raise PlanningError(f"Failed to validate tasks: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error in generate_plan: {e}", exc_info=True)
            error_message = f"Unexpected error generating plan: {e}. "
            if json_content_for_error:
                error_message += f"Problematic JSON content (approximate): {json_content_for_error[:200]}..."
            raise PlanningError(error_message) from e 