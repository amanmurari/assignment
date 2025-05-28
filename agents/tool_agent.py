import os
import logging
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from langchain.tools import tool

# Direct import from exceptions module
from exceptions import TaskExecutionError

# Initialize logger for this module
logger = logging.getLogger("agents")

@tool
def search(query: str) -> str:
    """Search the web for information."""
    logger.info(f"Performing web search for query: '{query}'")
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        results = client.search(query=query, max_results=5)
        logger.info(f"Search completed. Found {len(results.get('results', []))} results.")
        return results
    except ImportError as e:
        logger.error("TavilyClient import error. Is tavily-python installed?", exc_info=True)
        raise TaskExecutionError(task_id=query, error=f"Search tool import error: {e}")
    except Exception as e:
        logger.error(f"Error during web search for query '{query}': {e}", exc_info=True)
        raise TaskExecutionError(task_id=query, error=f"Search failed: {e}")

@tool
def calculator(expression: str) -> float:
    """Evaluate mathematical expressions."""
    logger.info(f"Calculator: Attempting to evaluate expression: '{expression}'")
    
    try:
        # Clean and validate the expression
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            invalid_chars = sorted(list(set(c for c in expression if c not in allowed_chars)))
            error_msg = f"Invalid characters found in expression: {invalid_chars}"
            logger.error(f"Calculator error: {error_msg} in expression '{expression}'")
            raise ValueError(error_msg)
        
        # Remove any whitespace
        expression_cleaned = expression.replace(" ", "")
        logger.debug(f"Calculator: Cleaned expression: '{expression_cleaned}'")
        
        # Basic security check
        if not expression_cleaned:
            error_msg = "Expression is empty after cleaning"
            logger.error(f"Calculator error: {error_msg} from original '{expression}'")
            raise ValueError(error_msg)
        if len(expression_cleaned) > 100:
            error_msg = f"Expression too long ({len(expression_cleaned)} chars) after cleaning"
            logger.error(f"Calculator error: {error_msg} from original '{expression}'")
            raise ValueError(error_msg)
        
        # Evaluate the expression
        logger.debug(f"Calculator: Evaluating expression '{expression_cleaned}'...")
        result = float(eval(expression_cleaned, {"__builtins__": {}}, {}))
        logger.info(f"Calculator: Expression '{expression_cleaned}' evaluated to {result}")
        return result
        
    except Exception as e:
        error_msg = f"Failed to evaluate expression '{expression}': {str(e)}"
        logger.error(f"Calculator error: {error_msg}", exc_info=True)
        raise

class ToolAgent:
    def __init__(self):
        self.tools = {
            "search": search,
            "calculator": calculator
        }
        logger.info("ToolAgent initialized with tools: search, calculator")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Executing task: {task}")
        task_id = task.get("id", "unknown_task")
        tool_name = task.get("tool")
        description = task.get("description")

        if not tool_name:
            logger.error(f"Task {task_id} missing 'tool' field. Task data: {task}")
            raise TaskExecutionError(task_id=str(task_id), error="Task missing tool field")
            
        if tool_name not in self.tools:
            logger.error(f"Task {task_id} specified an unknown tool: '{tool_name}'. Task data: {task}")
            raise TaskExecutionError(task_id=str(task_id), error=f"Unknown tool: {tool_name}")
        
        if description is None:
            logger.error(f"Task {task_id} (tool: {tool_name}) missing 'description' field for tool input. Task data: {task}")
            raise TaskExecutionError(task_id=str(task_id), error="Task missing description field for tool input")

        try:
            logger.debug(f"Attempting to execute tool '{tool_name}' for task {task_id} with description '{description}'")
            result = self.tools[tool_name](description)
            logger.info(f"Task {task_id} (tool: {tool_name}) executed successfully. Result: {str(result)[:100]}...")
            
            return {
                "task_id": task_id,
                "result": result,
                "status": "completed"
            }
        except RetryError as e:
            error_msg = f"Task {task_id} (tool: {tool_name}) failed after multiple retries: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "task_id": task_id,
                "result": error_msg,
                "status": "failed"
            }
        except Exception as e:
            error_msg = f"Error during execution of task {task_id} (tool: {tool_name}): {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "task_id": task_id,
                "result": error_msg,
                "status": "failed"
            } 