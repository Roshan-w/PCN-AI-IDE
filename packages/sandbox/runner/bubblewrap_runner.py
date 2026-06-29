# packages/sandbox/runner/bubblewrap_runner.py
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path
from enum import Enum

class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"

@dataclass
class SandboxConfig:
    timeout_seconds: int = 60
    max_memory_mb: int = 1024
    max_cpu_percent: int = 50
    allow_network: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    workspace_path: str = "/tmp/sandbox/workspace"
    read_only_paths: List[str] = field(default_factory=lambda: ["/usr", "/lib", "/lib64", "/bin"])
    env_vars: Dict[str, str] = field(default_factory=dict)
    disable_userns: bool = False
    enable_seccomp: bool = True

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    timeout: bool
    memory_exceeded: bool
    duration_ms: int
    artifacts: Dict[str, bytes] = field(default_factory=dict)

class BubblewrapSandbox:
    def __init__(self, config: SandboxConfig):
        self.config = config

    async def execute(
        self,
        code: str,
        language: Language,
        files: Optional[Dict[str, str]] = None,
        command: Optional[str] = None
    ) -> ExecutionResult:
        # Mock execution for compilation check
        return ExecutionResult(0, "success", "", False, False, 100)
