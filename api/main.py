from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import logging
import traceback
from uuid import uuid4

# Import from local modules using absolute imports
from workflow.main_workflow import run_workflow
from config.logging_config import setup_logging
from exceptions import (
    WorkflowException, APIError, TaskNotFoundError,
    InvalidRequestError, AsyncTaskError
)

# Load environment variables
load_dotenv()

# Set up logging
workflow_logger, agents_logger, api_logger = setup_logging()

# Validate required environment variables
required_env_vars = ["GROQ_API_KEY", "TAVILY_API_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    api_logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Create FastAPI app
app = FastAPI(
    title="Agentic Workflow API",
    description="API for executing agentic workflows using Langgraph",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:8000",  # FastAPI server (for production build)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active tasks
active_tasks: Dict[str, Dict[str, Any]] = {}

class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str
    detail: Optional[str] = None
    timestamp: str
    request_id: str
    path: str

class QueryRequest(BaseModel):
    """Request model for workflow queries."""
    query: str
    max_iterations: int = Field(default=3, ge=1, le=10)
    async_execution: bool = Field(default=False, description="Whether to run the query asynchronously")

class WorkflowResponse(BaseModel):
    """Response model for workflow results."""
    task_id: str
    success: bool
    response: str
    tasks: list
    results: list
    execution_time: float

class TaskStatus(BaseModel):
    """Model for task status response."""
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[WorkflowResponse] = None
    error: Optional[str] = None

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat(),
            request_id=str(uuid4()),
            path=request.url.path
        ).dict()
    )

@app.exception_handler(WorkflowException)
async def workflow_exception_handler(request: Request, exc: WorkflowException):
    """Handle workflow-specific exceptions."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, APIError):
        status_code = exc.status_code
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            detail=str(exc),
            timestamp=datetime.utcnow().isoformat(),
            request_id=str(uuid4()),
            path=request.url.path
        ).dict()
    )

def process_query_task(task_id: str, query: str, max_iterations: int):
    """Process a query in the background."""
    try:
        start_time = time.time()
        active_tasks[task_id]["status"] = "running"
        
        # Run workflow
        result = run_workflow(query, max_iterations)
        execution_time = time.time() - start_time
        
        # Create response
        response = WorkflowResponse(
            task_id=task_id,
            success=result["success"],
            response=result["response"],
            tasks=result["tasks"],
            results=result["results"],
            execution_time=execution_time
        )
        
        active_tasks[task_id].update({
            "status": "completed",
            "result": response.dict(),
            "completed_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        error_msg = f"Task processing failed: {str(e)}"
        api_logger.error(f"{error_msg}\n{traceback.format_exc()}")
        active_tasks[task_id].update({
            "status": "failed",
            "error": error_msg,
            "completed_at": datetime.utcnow().isoformat()
        })
        raise AsyncTaskError(error_msg)

@app.post("/query")
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Process a workflow query."""
    task_id = str(uuid4())
    api_logger.info(f"Processing query: {request.query} (Task ID: {task_id})")
    
    try:
        if request.async_execution:
            # Start async task
            active_tasks[task_id] = {
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "query": request.query
            }
            
            background_tasks.add_task(
                process_query_task,
                task_id,
                request.query,
                request.max_iterations
            )
            
            return TaskStatus(
                task_id=task_id,
                status="pending"
            ).dict()
        else:
            # Run synchronously
            start_time = time.time()
            result = run_workflow(request.query, request.max_iterations)
            execution_time = time.time() - start_time
            
            return WorkflowResponse(
                task_id=task_id,
                success=result["success"],
                response=result["response"],
                tasks=result["tasks"],
                results=result["results"],
                execution_time=execution_time
            ).dict()
            
    except Exception as e:
        api_logger.error(f"Error processing query: {str(e)}\n{traceback.format_exc()}")
        raise

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a task."""
    if task_id not in active_tasks:
        raise TaskNotFoundError(task_id)
    
    task = active_tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task["status"],
        result=task.get("result"),
        error=task.get("error")
    ).dict()

@app.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
) -> List[Dict[str, Any]]:
    """List all tasks with optional filtering."""
    tasks = []
    
    for task_id, task in active_tasks.items():
        if status and task["status"] != status:
            continue
            
        tasks.append(
            TaskStatus(
                task_id=task_id,
                status=task["status"],
                result=task.get("result"),
                error=task.get("error")
            ).dict()
        )
    
    # Apply pagination
    return tasks[offset:offset + limit]

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> Dict[str, str]:
    """Delete a task and its results."""
    if task_id not in active_tasks:
        raise TaskNotFoundError(task_id)
    
    del active_tasks[task_id]
    return {"status": "deleted"}

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Enhanced health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "active_tasks": len(active_tasks),
        "environment": {
            "groq_api_key": bool(os.getenv("GROQ_API_KEY")),
            "tavily_api_key": bool(os.getenv("TAVILY_API_KEY"))
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)