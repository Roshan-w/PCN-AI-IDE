import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path
from enum import Enum
import tempfile

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
        with tempfile.TemporaryDirectory(prefix="sandbox_") as workspace:
            workspace_path = Path(workspace)
            main_file = self._get_main_filename(language)
            (workspace_path / main_file).write_text(code)

            if files:
                for filename, content in files.items():
                    (workspace_path / filename).write_text(content)

            if command is None:
                command = self._build_command(language, main_file)

            bwrap_cmd = self._build_bwrap_command(workspace_path, command)

            start_time = time.time()
            try:
                proc = await asyncio.create_subprocess_exec(
                    *bwrap_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout_seconds
                )
                duration_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    exit_code=proc.returncode,
                    stdout=stdout.decode('utf-8', errors='replace'),
                    stderr=stderr.decode('utf-8', errors='replace'),
                    timeout=False,
                    memory_exceeded=False,
                    duration_ms=duration_ms
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ExecutionResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {self.config.timeout_seconds}s",
                    timeout=True,
                    memory_exceeded=False,
                    duration_ms=self.config.timeout_seconds * 1000
                )

    def _build_bwrap_command(self, workspace: Path, command: str) -> List[str]:
        cmd = [
            "bwrap",
            "--unshare-all",
            "--share-net" if self.config.allow_network else "--unshare-net",
            "--new-session",
            "--die-with-parent",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/bin", "/bin",
            "--bind", str(workspace), "/workspace",
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin:/bin",
            "--setenv", "HOME", "/tmp",
            "--setenv", "LANG", "C.UTF-8"
        ]

        for key, value in self.config.env_vars.items():
            cmd.extend(["--setenv", key, value])

        cmd.extend(["--", "sh", "-c", f"cd /workspace && {command}"])
        return cmd

    def _get_main_filename(self, language: Language) -> str:
        return {
            Language.PYTHON: "main.py",
            Language.JAVASCRIPT: "main.js",
            Language.TYPESCRIPT: "main.ts",
            Language.GO: "main.go",
            Language.RUST: "main.rs",
        }[language]

    def _build_command(self, language: Language, main_file: str) -> str:
        commands = {
            Language.PYTHON: f"python3 {main_file}",
            Language.JAVASCRIPT: f"node {main_file}",
            Language.TYPESCRIPT: f"npx tsx {main_file}",
            Language.GO: f"go run {main_file}",
            Language.RUST: f"rustc {main_file} -o main && ./main",
        }
        return commands[language]
