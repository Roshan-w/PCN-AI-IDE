from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import asyncio
import time
import json
import redis.asyncio as redis

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
    def __init__(self, redis_client: redis.Redis, config: Dict):
        self.redis = redis_client
        self.config = config
        self.workers: Dict[str, WorkerNode] = {}
        self._lock = asyncio.Lock()

    async def _fetch_workers_from_redis(self):
        worker_keys = await self.redis.keys("worker:*")
        workers = {}
        for key in worker_keys:
            data = await self.redis.get(key)
            if data:
                parsed = json.loads(data)
                workers[parsed["id"]] = WorkerNode(**parsed)
        return workers

    async def route_task(
        self,
        task_id: str,
        model: str,
        priority: int = 0,
        requirements: Optional[Dict] = None
    ) -> RoutingDecision:
        async with self._lock:
            self.workers = await self._fetch_workers_from_redis()

            candidates = []
            for worker in self.workers.values():
                if worker.status == WorkerStatus.OFFLINE or worker.status == WorkerStatus.DRAINING:
                    continue
                if worker.current_tasks >= worker.max_concurrent_tasks:
                    continue
                candidates.append(worker)

            if not candidates:
                raise NoWorkerAvailableError(f"No workers available for model {model}")

            # Simple scoring: prefer workers that already have the model loaded, then least tasks
            candidates.sort(key=lambda w: (-1 if model in w.loaded_models else 0, w.current_tasks))
            best_worker = candidates[0]

            # Update state in Redis
            best_worker.current_tasks += 1
            await self.redis.set(f"worker:{best_worker.id}", json.dumps(best_worker.__dict__))

            return RoutingDecision(
                worker_id=best_worker.id,
                reason="Best score based on capacity and affinity",
                estimated_wait_time=best_worker.current_tasks * 2.0,
                model_preloaded=model in best_worker.loaded_models
            )

    async def update_worker_status(self, worker_id: str, status: WorkerStatus, metrics: Dict):
        async with self._lock:
            data = await self.redis.get(f"worker:{worker_id}")
            if data:
                parsed = json.loads(data)
                worker = WorkerNode(**parsed)
                worker.status = status
                worker.gpu_utilization = metrics.get("gpu_utilization", 0.0)
                worker.memory_utilization = metrics.get("memory_utilization", 0.0)
                worker.loaded_models = metrics.get("loaded_models", [])
                worker.last_heartbeat = time.time()
                await self.redis.set(f"worker:{worker_id}", json.dumps(worker.__dict__))
