from typing import Dict, List, Any
from collections import deque

class TaskQueue:
    def __init__(self):
        self.tasks = deque()
        self.completed_tasks = {}
        self.failed_tasks = {}

    def add_task(self, task: Dict[str, Any]) -> None:
        """Add a new task to the queue."""
        task["status"] = "pending"
        self.tasks.append(task)

    def get_next_task(self) -> Dict[str, Any]:
        """Get the next task from the queue."""
        if not self.tasks:
            return None
        return self.tasks[0]

    def mark_task_completed(self, task_id: int, result: Any) -> None:
        """Mark a task as completed with its result."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "completed"
                self.completed_tasks[task_id] = {
                    "task": task,
                    "result": result
                }
                self.tasks.remove(task)
                break

    def mark_task_failed(self, task_id: int, error: str) -> None:
        """Mark a task as failed with error details."""
        for task in self.tasks:
            if task["id"] == task_id:
                task["status"] = "failed"
                self.failed_tasks[task_id] = {
                    "task": task,
                    "error": error
                }
                self.tasks.remove(task)
                break

    def retry_task(self, task_id: int) -> None:
        """Move a failed task back to the queue for retry."""
        if task_id in self.failed_tasks:
            task = self.failed_tasks[task_id]["task"]
            task["status"] = "pending"
            task["retry_count"] = task.get("retry_count", 0) + 1
            self.tasks.append(task)
            del self.failed_tasks[task_id]

    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tasks grouped by status."""
        return {
            "pending": list(self.tasks),
            "completed": list(self.completed_tasks.values()),
            "failed": list(self.failed_tasks.values())
        }

    def is_empty(self) -> bool:
        """Check if there are no pending tasks."""
        return len(self.tasks) == 0 