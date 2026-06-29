from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

# ============================================================================
# Task Models
# ============================================================================
class TaskStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskMode(str, Enum):
    SAFE = "safe"       # All changes require approval
    DIRECT = "direct"   # Changes applied automatically

@dataclass
class Task:
    """Primary task entity."""
    id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    user_id: str = ""

    # Input
    prompt: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    mode: TaskMode = TaskMode.SAFE
    # State
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    current_stage: str = ""
    # Decomposition
    subtasks: List['SubTask'] = field(default_factory=list)
    current_subtask_idx: int = 0
    # Results
    artifacts: List['CodeArtifact'] = field(default_factory=list)
    evidence_bundle_id: Optional[UUID] = None
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    # Routing
    assigned_workers: List[str] = field(default_factory=list)
    model_used: str = ""
    # Metrics
    tokens_generated: int = 0
    inference_time_ms: int = 0
    total_time_ms: int = 0

@dataclass
class SubTask:
    """Decomposed subtask."""
    id: UUID = field(default_factory=uuid4)
    parent_task_id: UUID = field(default_factory=uuid4)
    description: str = ""
    assigned_agent: str = ""
    dependencies: List[UUID] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    result: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

# ============================================================================
# Code Artifact Models
# ============================================================================
class ChangeAction(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"

@dataclass
class CodeArtifact:
    """Generated or modified code file."""
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    subtask_id: Optional[UUID] = None
    path: str = ""
    language: str = ""
    action: ChangeAction = ChangeAction.CREATE
    # Content
    content: str = ""
    original_content: Optional[str] = None  # For modify actions
    diff: str = ""
    # Approval (for Safe Mode)
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    # Audit
    security_reviewed: bool = False
    quality_reviewed: bool = False

# ============================================================================
# Evidence Bundle Models
# ============================================================================
@dataclass
class EvidenceEntry:
    """Single piece of evidence in the audit trail."""
    id: UUID = field(default_factory=uuid4)
    bundle_id: UUID = field(default_factory=uuid4)
    agent: str = ""
    action: str = ""
    reasoning: str = ""
    # Artifacts
    input_snapshot: Optional[str] = None
    output_snapshot: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    # Metadata
    model_used: str = ""
    tokens_used: int = 0
    duration_ms: int = 0

@dataclass
class EvidenceBundle:
    """Complete audit trail for a task."""
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    entries: List[EvidenceEntry] = field(default_factory=list)
    # Summary
    total_tokens: int = 0
    total_duration_ms: int = 0
    agents_involved: List[str] = field(default_factory=list)
    # Export
    export_format: str = "json"
    exported_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

# ============================================================================
# Project Models
# ============================================================================
@dataclass
class Project:
    """Project/workspace entity."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    repository_url: Optional[str] = None
    # Configuration
    design_protocol: str = "tailwind_shadcn"
    default_mode: TaskMode = TaskMode.SAFE
    # Access
    owner_id: str = ""
    member_ids: List[str] = field(default_factory=list)
    # RAG
    qdrant_collection: str = ""
    indexing_enabled: bool = True
    last_indexed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

# ============================================================================
# Worker Models
# ============================================================================
class WorkerStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    DRAINING = "draining"
    ERROR = "error"

@dataclass
class WorkerNode:
    """Worker node registration."""
    id: str = ""
    hostname: str = ""
    ip_address: str = ""
    status: WorkerStatus = WorkerStatus.OFFLINE
    # Capacity
    max_concurrent_tasks: int = 4
    current_tasks: int = 0
    # Hardware
    gpu_model: str = ""
    gpu_memory_mb: int = 0
    system_memory_mb: int = 0
    # Models
    loaded_models: List[str] = field(default_factory=list)
    available_models: List[str] = field(default_factory=list)
    # Metrics
    gpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    # Health
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    error_count: int = 0
    registered_at: datetime = field(default_factory=datetime.utcnow)
