# packages/orchestrator/router/task_router.py
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import asyncio
import time

class WorkerStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    DRAINING = "draining"

@dataclass
class WorkerNode:
    id: str
    host: str
    port: int
    status: WorkerStatus
    current_tasks: int
    max_concurrent_tasks: int
    gpu_utilization: float
    memory_utilization: float
    loaded_models: List[str]
    last_heartbeat: float

@dataclass
class RoutingDecision:
    worker_id: str
    reason: str
    estimated_wait_time: float
    model_preloaded: bool

class NoWorkerAvailableError(Exception):
    pass

class TaskRouter:
    def __init__(self, redis_client, config: Dict):
        self.redis = redis_client
        self.config = config
        self.workers: Dict[str, WorkerNode] = {}
        self._lock = asyncio.Lock()

    async def route_task(
        self,
        task_id: str,
        model: str,
        priority: int = 0,
        requirements: Optional[Dict] = None
    ) -> RoutingDecision:
        async with self._lock:
            if not self.workers:
                raise NoWorkerAvailableError(f"No workers available for model {model}")

            best_worker = next(iter(self.workers.values()))
            return RoutingDecision(best_worker.id, "Mock routing", 0.0, True)

    async def update_worker_status(self, worker_id: str, status: WorkerStatus, metrics: Dict):
        async with self._lock:
            if worker_id in self.workers:
                worker = self.workers[worker_id]
                worker.status = status
