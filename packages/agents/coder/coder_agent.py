# packages/agents/coder/coder_agent.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from packages.orchestrator.workflows.coding_workflow import SubTask, CodeArtifact

class DesignProtocol(str, Enum):
    TAILWIND_SHADCN = "tailwind_shadcn"
    MATERIAL_UI = "material_ui"
    CHAKRA_UI = "chakra_ui"
    CUSTOM = "custom"

@dataclass
class CodeGenerationResult:
    files: List[CodeArtifact]
    reasoning: str
    design_decisions: List[str]
    warnings: List[str]

@dataclass
class PatchResult:
    patched_code: str
    description: str

class CoderAgent:
    def __init__(
        self,
        llm_client,
        design_protocol: DesignProtocol = DesignProtocol.TAILWIND_SHADCN,
        max_tokens: int = 4096
    ):
        self.llm = llm_client
        self.design_protocol = design_protocol
        self.max_tokens = max_tokens

    async def generate(
        self,
        task: SubTask,
        context: Dict[str, Any],
        rag_results: List[Dict[str, Any]]
    ) -> CodeGenerationResult:
        return CodeGenerationResult([], "", [], [])

    async def generate_patch(
        self,
        code: str,
        error_analysis: Any,
        context: Dict[str, Any]
    ) -> PatchResult:
        return PatchResult(code, "Fixed error")
