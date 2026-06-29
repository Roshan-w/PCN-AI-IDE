import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from packages.orchestrator.workflows.coding_workflow import SubTask, CodeArtifact
from openai import AsyncOpenAI

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
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "empty",
        model: str = "qwen-2.5-coder-7b-instruct",
        design_protocol: DesignProtocol = DesignProtocol.TAILWIND_SHADCN,
        max_tokens: int = 4096
    ):
        self.llm = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.design_protocol = design_protocol
        self.max_tokens = max_tokens

    async def generate(
        self,
        task: SubTask,
        context: Dict[str, Any],
        rag_results: List[Dict[str, Any]]
    ) -> CodeGenerationResult:
        system_prompt = self._build_system_prompt()
        user_prompt = f"Implement the following subtask:\n{task.description}\nContext: {context}\n\nPlease wrap your generated code in markdown blocks with the filename as a comment on the first line."

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=self.max_tokens
        )

        content = response.choices[0].message.content
        artifacts = []

        # Regex to extract markdown code blocks
        pattern = r"```(?P<language>\w+)?\n(?P<code>.*?)```"
        matches = re.finditer(pattern, content, re.DOTALL)

        for idx, match in enumerate(matches):
            lang = match.group("language") or "text"
            code = match.group("code").strip()

            # Try to extract filename from first line comment
            path = f"file_{idx}.txt"
            first_line = code.split('\n')[0]
            if first_line.startswith("# ") or first_line.startswith("// "):
                possible_path = first_line[2:].strip()
                if "." in possible_path:
                    path = possible_path

            artifacts.append(CodeArtifact(path=path, language=lang, content=code, diff=""))

        if not artifacts:
            # Fallback if LLM doesn't use blocks
            artifacts.append(CodeArtifact(path="output.txt", language="text", content=content, diff=""))

        return CodeGenerationResult(artifacts, content, [], [])

    def _build_system_prompt(self) -> str:
        base = "You are an expert software engineer generating production-quality code."
        if self.design_protocol == DesignProtocol.TAILWIND_SHADCN:
            return base + "\nRules: Use Tailwind CSS and Shadcn/ui. Ensure accessibility."
        return base

    async def generate_patch(
        self,
        code: str,
        error_analysis: Any,
        context: Dict[str, Any]
    ) -> PatchResult:
        prompt = f"Fix this code based on error analysis.\nCode: {code}\nAnalysis: {error_analysis.suggested_fix}\nProvide only the fixed code wrapped in a markdown block."
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content

        pattern = r"```(?P<language>\w+)?\n(?P<code>.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            patched_code = match.group("code").strip()
        else:
            patched_code = content

        return PatchResult(patched_code, error_analysis.suggested_fix)
