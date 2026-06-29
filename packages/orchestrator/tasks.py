from typing import Dict, Any
import json
import redis
from celery import Celery
import asyncio
from asgiref.sync import async_to_sync

redis_sync = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
celery_app = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@celery_app.task(name='process_task')
def process_task(
    task_id: str,
    prompt: str,
    project_id: str,
    mode: str,
    context: Dict[str, Any] = None,
    options: Dict[str, Any] = None,
    user_id: str = None
):
    """
    Real Celery task for processing a coding task via LangGraph.
    """
    redis_sync.publish(f"task_updates:{task_id}", json.dumps({"type": "status", "stage": "init", "progress": 0.05, "message": "Task picked up by worker"}))

    try:
        from packages.orchestrator.workflows.coding_workflow import create_coding_workflow
        workflow = create_coding_workflow()

        initial_state = {
            "task_id": task_id,
            "prompt": prompt,
            "project_id": project_id,
            "mode": mode,
            "context_files": context.get("files", []) if context else [],
            "repository_context": context or {},
            "rag_results": [],
            "subtasks": [],
            "current_subtask_idx": 0,
            "artifacts": [],
            "sandbox_results": [],
            "audit_results": [],
            "visual_review_results": [],
            "evidence_bundle": [],
            "retry_count": 0,
            "max_retries": 3,
            "status": "started",
            "error": None
        }

        # Use async_to_sync to run the async graph inside the synchronous Celery worker
        config = {"configurable": {"thread_id": task_id}}
        result = async_to_sync(workflow.ainvoke)(initial_state, config=config)

        redis_sync.publish(f"task_updates:{task_id}", json.dumps({"type": "status", "stage": "completed", "progress": 1.0, "message": "Task workflow complete"}))
        redis_sync.set(f"task:{task_id}", json.dumps({"status": "completed"}))

        # Serialize result appropriately for Celery
        return {"status": "completed", "task_id": task_id}
    except Exception as e:
        redis_sync.publish(f"task_updates:{task_id}", json.dumps({"type": "error", "message": str(e)}))
        redis_sync.set(f"task:{task_id}", json.dumps({"status": "failed", "error": str(e)}))
        raise e
