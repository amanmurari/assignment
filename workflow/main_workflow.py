from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph
import json
import logging

from agents.planner_agent import PlannerAgent
from agents.tool_agent import ToolAgent
from agents.reflector_agent import ReflectorAgent
from exceptions import WorkflowException, PlanningError, TaskExecutionError, ReflectionError, JSONParsingError

logger = logging.getLogger("workflow")

class WorkflowState(TypedDict):
    """State definition for the workflow."""
    query: str
    tasks: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    reflection: Dict[str, Any]
    final_response: str
    iteration: int
    max_iterations: int
    error_message: str

def create_workflow() -> StateGraph:
    logger.info("Creating main workflow graph.")
    
    planner = PlannerAgent()
    tool_agent = ToolAgent()
    reflector = ReflectorAgent()
    
    def plan_step(state: WorkflowState) -> WorkflowState:
        logger.info(f"Workflow: Initiating planning for query: '{state['query']}'")
        try:
            tasks = planner.generate_plan(state["query"])
            state["tasks"] = tasks
            logger.info(f"Workflow: Planning completed. {len(tasks)} tasks generated.")
        except (PlanningError, JSONParsingError) as e:
            logger.error(f"Workflow: Error during planning phase: {e}", exc_info=True)
            state["tasks"] = []
            state["error_message"] = f"Critical error during task planning: {e}"
        except Exception as e:
            logger.error(f"Workflow: Unexpected error during planning phase: {e}", exc_info=True)
            state["tasks"] = []
            state["error_message"] = f"Unexpected critical error during task planning: {e}"
        return state

    def execute_step(state: WorkflowState) -> WorkflowState:
        logger.info(f"Workflow: Initiating execution of {len(state.get('tasks', []))} tasks.")
        if not state.get("tasks"):
            logger.warning("Workflow: No tasks to execute. Skipping execution step.")
            state["results"] = []
            if not state.get("error_message"):
                 state["error_message"] = "Planning failed to produce any tasks."
            return state
        
        results = []
        current_tasks = state.get("tasks", [])
        for i, task in enumerate(current_tasks):
            logger.info(f"Workflow: Executing task {i+1}/{len(current_tasks)}: {task.get('id')}")
            try:
                result = tool_agent.execute_task(task)
                results.append(result)
                logger.info(f"Workflow: Task {task.get('id')} execution result: {result.get('status')}")
            except TaskExecutionError as e:
                logger.error(f"Workflow: Critical error executing task {task.get('id')}: {e}", exc_info=True)
                results.append({"task_id": task.get("id"), "result": str(e), "status": "failed_critically"})
            except Exception as e:
                logger.error(f"Workflow: Unexpected error executing task {task.get('id')}: {e}", exc_info=True)
                results.append({"task_id": task.get("id"), "result": f"Unexpected error: {e}", "status": "failed_unexpectedly"})
        
        state["results"] = results
        logger.info(f"Workflow: Execution step completed. {len(results)} results obtained.")
        return state

    def reflect_step(state: WorkflowState) -> WorkflowState:
        logger.info("Workflow: Initiating reflection on execution results.")
        if not state.get("results") and not state.get("error_message"):
            logger.warning("Workflow: No results to reflect upon and no planning error. This might indicate an issue or empty plan.")
            state["reflection"] = {"success": False, "complete": False, "feedback": "No tasks were executed or no results produced.", "refinements": []}
            if not state.get("tasks"):
                state["reflection"]["feedback"] = "No tasks were planned."
            return state
        elif state.get("error_message"):
             logger.warning(f"Workflow: Critical error occurred ('{state.get('error_message')}'). Bypassing LLM reflection.")
             state["reflection"] = {"success": False, "complete": False, "feedback": state.get("error_message"), "refinements": []}
             return state

        try:
            reflection_output = reflector.evaluate_results(
                state["query"],
                state.get("tasks", []),
                state.get("results", [])
            )
            state["reflection"] = reflection_output
            logger.info("Workflow: Reflection completed.")
        except (ReflectionError, JSONParsingError) as e:
            logger.error(f"Workflow: Error during reflection phase: {e}", exc_info=True)
            state["reflection"] = {"success": False, "complete": False, "feedback": f"Critical error during result reflection: {e}", "refinements": []}
            state["error_message"] = f"Critical error during result reflection: {e}"
        except Exception as e:
            logger.error(f"Workflow: Unexpected error during reflection phase: {e}", exc_info=True)
            state["reflection"] = {"success": False, "complete": False, "feedback": f"Unexpected critical error during result reflection: {e}", "refinements": []}
            state["error_message"] = f"Unexpected critical error during result reflection: {e}"
        return state

    def should_continue_decision(state: WorkflowState) -> str:
        state["iteration"] = state.get("iteration", 0) + 1
        logger.info(f"Workflow: Iteration {state['iteration']}/{state['max_iterations']}. Making decision to continue or end.")

        # Always end if there's an error
        if state.get("error_message"):
            logger.warning(f"Workflow: Critical error detected ('{state.get('error_message')}'). Ending workflow.")
            return "end_workflow"

        # End if max iterations reached
        if state["iteration"] >= state["max_iterations"]:
            logger.info("Workflow: Max iterations reached. Ending workflow.")
            return "end_workflow"
            
        reflection = state.get("reflection", {})
        
        # End if reflection indicates success
        if reflection.get("complete") and reflection.get("success"):
            logger.info("Workflow: Reflection indicates completion and success. Ending workflow.")
            return "end_workflow"
            
        # Check if all tasks were successful
        results = state.get("results", [])
        all_tasks_successful = all(r.get("status") == "completed" for r in results)
        
        # If all tasks were successful but reflection doesn't indicate completion,
        # end to prevent infinite loops
        if all_tasks_successful and not reflection.get("complete"):
            logger.info("Workflow: All tasks successful but not marked complete. Ending to prevent loop.")
            return "end_workflow"
            
        # Only continue if there are actual refinements and we haven't hit limits
        if reflection.get("refinements") and state["iteration"] < state["max_iterations"]:
            logger.info("Workflow: Refinements suggested and within iteration limit. Continuing to refine step.")
            return "refine_tasks"
            
        logger.info("Workflow: No valid reason to continue. Ending workflow.")
        return "end_workflow"

    def refine_step(state: WorkflowState) -> WorkflowState:
        logger.info("Workflow: Initiating task refinement based on reflection.")
        refinements = state.get("reflection", {}).get("refinements", [])
        current_tasks = state.get("tasks", [])[:]
        refined_tasks_count = 0

        if not refinements:
            logger.info("Workflow: No refinement instructions provided. Tasks remain unchanged.")
            state["tasks"] = current_tasks
            return state

        new_task_id_counter = max([t.get("id", 0) for t in current_tasks if isinstance(t.get("id"), int)], default=0) + 1

        for refinement in refinements:
            action = refinement.get("action")
            task_id_to_act_on = refinement.get("task_id")
            details_str = refinement.get("details")
            logger.debug(f"Workflow: Applying refinement: Action='{action}', TaskID='{task_id_to_act_on}', Details='{details_str}'")

            try:
                if action == "remove" and task_id_to_act_on is not None:
                    original_len = len(current_tasks)
                    current_tasks = [t for t in current_tasks if t.get("id") != task_id_to_act_on]
                    if len(current_tasks) < original_len:
                        logger.info(f"Workflow: Removed task ID {task_id_to_act_on}.")
                        refined_tasks_count += 1
                elif action == "modify" and task_id_to_act_on is not None and details_str:
                    details = json.loads(details_str)
                    modified = False
                    for task in current_tasks:
                        if task.get("id") == task_id_to_act_on:
                            logger.info(f"Workflow: Modifying task ID {task_id_to_act_on} with details: {details}")
                            task.update(details)
                            modified = True
                            refined_tasks_count += 1
                            break
                    if not modified:
                        logger.warning(f"Workflow: Task ID {task_id_to_act_on} not found for modification.")
                elif action == "add" and details_str:
                    new_task_details = json.loads(details_str)
                    if "id" not in new_task_details or new_task_details["id"] is None:
                        new_task_details["id"] = new_task_id_counter
                        new_task_id_counter += 1
                    if not all(k in new_task_details for k in ["id", "description", "tool"]):
                        logger.error(f"Workflow: Added task details {new_task_details} missing required fields (id, description, tool). Skipping add.")
                        continue
                    current_tasks.append(new_task_details)
                    logger.info(f"Workflow: Added new task: {new_task_details}")
                    refined_tasks_count += 1
                else:
                    logger.warning(f"Workflow: Unknown or incomplete refinement action: {refinement}")
            except json.JSONDecodeError as e:
                logger.error(f"Workflow: Failed to parse JSON details for refinement action '{action}': {details_str}. Error: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Workflow: Error applying refinement {refinement}: {e}", exc_info=True)
        
        state["tasks"] = current_tasks
        logger.info(f"Workflow: Refinement step completed. {refined_tasks_count} refinements applied. Total tasks now: {len(current_tasks)}.")
        state["results"] = []
        state["reflection"] = {}
        state["error_message"] = ""
        return state

    def generate_response_step(state: WorkflowState) -> WorkflowState:
        logger.info("Workflow: Generating final response.")
        
        if state.get("error_message"):
            logger.error(f"Workflow: Final response reflects critical error: {state.get('error_message')}")
            state["final_response"] = state.get("error_message")
            return state

        results = state.get("results", [])
        successful_results_data = [r.get("result") for r in results if r.get("status") == "completed"]
        failed_tasks_info = [f"Task {r.get('task_id')} failed: {r.get('result')}" for r in results if r.get("status") not in ["completed", None]]

        response_parts = []
        if successful_results_data:
            response_parts.append("Successfully completed tasks yielded:")
            for i, res_data in enumerate(successful_results_data, 1):
                response_parts.append(f"{i}. {str(res_data)[:500]}")
        
        if failed_tasks_info:
            response_parts.append("\nSome tasks encountered issues:")
            for info in failed_tasks_info:
                response_parts.append(info)

        if not response_parts:
            final_feedback = state.get("reflection", {}).get("feedback", "Workflow concluded. No specific results to report.")
            response_parts.append(final_feedback)
            if not state.get("tasks") and not state.get("results") :
                 response_parts.append("No tasks were planned or executed.")

        state["final_response"] = "\n".join(response_parts).strip()
        logger.info(f"Workflow: Final response generated: {state['final_response'][:200]}...")
        return state

    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("plan", plan_step)
    workflow.add_node("execute", execute_step)
    workflow.add_node("reflect", reflect_step)
    workflow.add_node("refine", refine_step)
    workflow.add_node("generate_response", generate_response_step)
    
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "execute")
    workflow.add_edge("execute", "reflect")
    
    workflow.add_conditional_edges(
        "reflect",
        should_continue_decision,
        {
            "refine_tasks": "refine",
            "end_workflow": "generate_response"
        }
    )
    workflow.add_edge("refine", "execute")
    workflow.set_finish_point("generate_response")
    
    # Set recursion limit before compiling
    workflow.config = {"recursion_limit": 50}
    
    logger.info("Workflow graph compiled.")
    return workflow.compile()

def run_workflow(query: str, max_iterations: int = 3) -> Dict[str, Any]:
    logger.info(f"Running workflow for query: '{query}', max_iterations: {max_iterations}")
    workflow_graph = create_workflow()
    
    initial_state = WorkflowState(
        query=query,
        tasks=[],
        results=[],
        reflection={},
        final_response="",
        iteration=0,
        max_iterations=max_iterations,
        error_message=""
    )
    
    final_state = None
    try:
        final_state = workflow_graph.invoke(initial_state)
        logger.info("Workflow invocation completed.")
        return {
            "success": not bool(final_state.get("error_message")),
            "response": final_state.get("final_response", "Workflow did not produce a final response."),
            "tasks": final_state.get("tasks", []),
            "results": final_state.get("results", [])
        }
    except WorkflowException as e:
        logger.error(f"WorkflowException during workflow run: {e}", exc_info=True)
        return {"success": False, "response": f"Workflow error: {e}", "tasks": [], "results": []}
    except Exception as e:
        logger.error(f"Unexpected error during workflow run: {e}", exc_info=True)
        tasks_at_error = final_state.get("tasks", []) if final_state else []
        results_at_error = final_state.get("results", []) if final_state else []
        return {"success": False, "response": f"Unexpected workflow error: {e}", "tasks": tasks_at_error, "results": results_at_error} 