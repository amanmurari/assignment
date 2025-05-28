"""Custom exceptions for the agentic workflow."""

class WorkflowException(Exception):
    """Base exception for workflow-related errors."""
    pass

class PlanningError(WorkflowException):
    """Raised when there's an error in task planning."""
    pass

class TaskValidationError(WorkflowException):
    """Raised when task validation fails."""
    def __init__(self, task_data: dict, message: str):
        self.task_data = task_data
        self.message = message
        super().__init__(f"{message}: {task_data}")

class JSONParsingError(WorkflowException):
    """Raised when JSON parsing fails."""
    def __init__(self, content: str, error: str):
        self.content = content
        self.error = error
        super().__init__(f"Failed to parse JSON: {error}\nContent: {content}")

class TaskExecutionError(WorkflowException):
    """Raised when task execution fails."""
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error
        super().__init__(f"Task {task_id} failed: {error}")

class ReflectionError(WorkflowException):
    """Raised when reflection fails."""
    pass

class InvalidTaskStateError(WorkflowException):
    """Raised when task state is invalid."""
    pass

class EnvironmentError(WorkflowException):
    """Raised when environment configuration is invalid."""
    pass

class APIError(WorkflowException):
    """Base exception for API-related errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.status_code = status_code
        super().__init__(message)

class TaskNotFoundError(APIError):
    """Raised when a requested task is not found."""
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task {task_id} not found",
            status_code=404
        )

class InvalidRequestError(APIError):
    """Raised when the request is invalid."""
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400
        )

class AsyncTaskError(APIError):
    """Raised when there's an error with async task processing."""
    pass 