import pytest
from typing import Dict, Any
from ..agents.task_manager import TaskQueue
from ..agents.planner_agent import PlannerAgent
from ..agents.tool_agent import ToolAgent
from ..agents.reflector_agent import ReflectorAgent
from ..workflows.main_workflow import create_workflow

def test_task_queue():
    """Test TaskQueue functionality."""
    queue = TaskQueue()
    
    # Test adding tasks
    task = {"id": 1, "description": "Test task", "tool": "calculator"}
    queue.add_task(task)
    assert len(queue.tasks) == 1
    assert queue.tasks[0]["status"] == "pending"
    
    # Test completing tasks
    queue.mark_task_completed(1, "result")
    assert len(queue.tasks) == 0
    assert len(queue.completed_tasks) == 1
    
    # Test task retrieval
    all_tasks = queue.get_all_tasks()
    assert len(all_tasks["completed"]) == 1
    assert len(all_tasks["pending"]) == 0
    assert len(all_tasks["failed"]) == 0

def test_planner_agent():
    """Test PlannerAgent task breakdown."""
    planner = PlannerAgent()
    query = "What is 2 plus 2?"
    plan = planner.generate_plan(query)
    
    assert isinstance(plan, list)
    assert len(plan) > 0
    assert all(isinstance(task, dict) for task in plan)
    assert all("id" in task and "description" in task and "tool" in task for task in plan)

def test_tool_agent():
    """Test ToolAgent execution."""
    agent = ToolAgent()
    task = {
        "id": 1,
        "description": "2 + 2",
        "tool": "calculator"
    }
    
    result = agent.execute_task(task)
    assert result["status"] == "completed"
    assert result["result"] == 4.0

def test_reflector_agent():
    """Test ReflectorAgent analysis."""
    reflector = ReflectorAgent()
    task = {
        "id": 1,
        "description": "Calculate 2 + 2",
        "tool": "calculator"
    }
    result = 4.0
    
    feedback = reflector.analyze_result(task, result)
    assert isinstance(feedback, dict)
    assert "task_id" in feedback
    assert "feedback" in feedback
    assert "is_accurate" in feedback["feedback"]

def test_workflow_integration():
    """Test full workflow integration."""
    workflow = create_workflow()
    
    initial_state = {
        "user_query": "What is 2 plus 2?",
        "plan": [],
        "current_task_index": 0,
        "results": {},
        "feedback": {},
        "task_queue": TaskQueue()
    }
    
    final_state = workflow.invoke(initial_state)
    
    assert isinstance(final_state, dict)
    assert len(final_state["results"]) > 0
    assert len(final_state["feedback"]) > 0

if __name__ == "__main__":
    pytest.main([__file__]) 