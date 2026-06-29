import json
import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime, timezone
import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field
from enum import Enum

# Real Redis Client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

async def get_current_user_id(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        # Fallback for development if no auth provided, but this is a real implementation stub
        return "unauthenticated-user"
    # Simple token extraction for demonstration
    token = auth_header.replace("Bearer ", "")
    # In production, validate JWT signature here.
    return token

async def validate_ws_token(token: str) -> Optional[str]:
    if not token or token == "invalid":
        return None
    return token

async def subscribe_to_task_updates(task_id: UUID) -> AsyncGenerator[Dict[str, Any], None]:
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"task_updates:{task_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(f"task_updates:{task_id}")
        await pubsub.close()

app = FastAPI(
    title="PCN AI IDE API",
    version="1.0.0",
    description="Private Cluster Network AI IDE API Gateway"
)

# ============================================================================
# Data Models
# ============================================================================
class TaskMode(str, Enum):
    SAFE = "safe"
    DIRECT = "direct"

class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskSubmission(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    project_id: UUID
    mode: TaskMode = TaskMode.SAFE
    context: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    task_id: UUID
    status: TaskStatus
    created_at: datetime
    websocket_url: str

class TaskDetail(BaseModel):
    task_id: UUID
    status: str
    details: Optional[Dict[str, Any]] = None

class ChangeApproval(BaseModel):
    approved: bool

class ChangeRejection(BaseModel):
    reason: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7

class CompletionRequest(BaseModel):
    model: str
    prompt: str
    max_tokens: Optional[int] = 100

class EvidenceEntryResponse(BaseModel):
    agent: str
    decision: str
    reasoning: str
    timestamp: datetime
    artifacts: Optional[List[str]] = None

# ============================================================================
# REST Endpoints
# ============================================================================
@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=202)
async def submit_task(
    task: TaskSubmission,
    user_id: str = Depends(get_current_user_id)
) -> TaskResponse:
    task_id = uuid4()

    # Store initial state in Redis
    await redis_client.set(f"task:{task_id}", json.dumps({
        "status": TaskStatus.QUEUED.value,
        "project_id": str(task.project_id),
        "user_id": user_id
    }))

    # Enqueue real Celery task
    try:
        from packages.orchestrator.tasks import process_task
        process_task.delay(
            task_id=str(task_id),
            prompt=task.prompt,
            project_id=str(task.project_id),
            mode=task.mode.value,
            context=task.context,
            options=task.options,
            user_id=user_id
        )
    except Exception as e:
        print(f"Error submitting celery task: {e}")

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        websocket_url=f"wss://api.pcn-ai-ide.local/ws/tasks/{task_id}"
    )

@app.get("/api/v1/tasks/{task_id}", response_model=TaskDetail)
async def get_task_status(task_id: UUID) -> TaskDetail:
    data = await redis_client.get(f"task:{task_id}")
    if data:
        parsed = json.loads(data)
        return TaskDetail(task_id=task_id, status=parsed.get("status", "unknown"), details=parsed)
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/api/v1/tasks/{task_id}/evidence", response_model=List[EvidenceEntryResponse])
async def get_task_evidence(task_id: UUID) -> List[EvidenceEntryResponse]:
    # Placeholder for database fetching
    return []

@app.post("/api/v1/tasks/{task_id}/approve", status_code=200)
async def approve_changes(
    task_id: UUID,
    approval: ChangeApproval,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    await redis_client.set(f"task:{task_id}:approval", json.dumps({"approved": approval.approved}))
    # Publish to unblock workflow
    await redis_client.publish(f"task_approval:{task_id}", json.dumps({"approved": approval.approved}))
    return {"status": "approved" if approval.approved else "not_approved"}

@app.post("/api/v1/tasks/{task_id}/reject", status_code=200)
async def reject_changes(
    task_id: UUID,
    rejection: ChangeRejection,
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    await redis_client.set(f"task:{task_id}:approval", json.dumps({"approved": False, "reason": rejection.reason}))
    await redis_client.publish(f"task_approval:{task_id}", json.dumps({"approved": False}))
    return {"status": "rejected"}

# ============================================================================
# WebSocket Endpoints
# ============================================================================
@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(
    websocket: WebSocket,
    task_id: UUID,
    token: str = Query(...)
):
    await websocket.accept()
    user_id = await validate_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    try:
        async for message in subscribe_to_task_updates(task_id):
            await websocket.send_json(message)
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        await websocket.close()

# ============================================================================
# OpenAI-Compatible Proxy (Optional)
# ============================================================================
import httpx

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/v1/chat/completions", json=body)
        return response.json()

@app.post("/v1/completions")
async def completions(request: Request):
    body = await request.json()
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8000/v1/completions", json=body)
        return response.json()

@app.get("/v1/models")
async def list_models():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/v1/models")
        return response.json()
