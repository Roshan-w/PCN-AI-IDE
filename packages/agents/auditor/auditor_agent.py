import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from packages.orchestrator.workflows.coding_workflow import CodeArtifact
from openai import AsyncOpenAI

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class Finding:
    severity: Severity
    category: str
    file: str
    line: int
    message: str
    recommendation: str
    cwe_id: Optional[str] = None
    id: Optional[str] = None

@dataclass
class AuditResult:
    approved: bool
    findings: List[Finding]
    fixable: bool
    summary: str

@dataclass
class ErrorAnalysis:
    error_type: str
    root_cause: str
    suggested_fix: str
    fixable: bool

class AuditorAgent:
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "empty",
        model: str = "qwen-2.5-coder-7b-instruct",
        config: Optional[Dict] = None
    ):
        self.llm = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.config = config or {}

    async def audit(
        self,
        code_artifacts: List[CodeArtifact],
        context: Dict[str, Any]
    ) -> AuditResult:
        all_findings = []
        for artifact in code_artifacts:
            prompt = f"""Perform security review of this code.
File: {artifact.path}
Language: {artifact.language}
Code:
{artifact.content}

Output findings in JSON format:
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "security",
      "line": 10,
      "message": "description",
      "recommendation": "fix suggestion",
      "cwe_id": "CWE-123"
    }}
  ]
}}
If the code is perfectly secure, output {{"findings": []}}"""
            try:
                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                content = response.choices[0].message.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                data = json.loads(content)
                for item in data.get("findings", []):
                    item["file"] = artifact.path
                    all_findings.append(Finding(**item))
            except Exception as e:
                print(f"Auditor JSON parse error: {e}")
                # Fallback mapping if parsing fails
                all_findings.append(Finding(Severity.MEDIUM, "security", artifact.path, 0, f"Parse error from LLM: {e}", "Review manually"))

        critical_issues = [f for f in all_findings if f.severity == Severity.CRITICAL]
        high_issues = [f for f in all_findings if f.severity == Severity.HIGH]

        approved = len(critical_issues) == 0 and len(high_issues) <= 2
        fixable = all(f.severity != Severity.CRITICAL for f in all_findings)

        return AuditResult(approved, all_findings, fixable, "Audit completed")

    async def analyze_error(
        self,
        code: str,
        error_message: str,
        context: Dict[str, Any]
    ) -> ErrorAnalysis:
        prompt = f"""Analyze this error and suggest a fix.
Code:
{code}
Error:
{error_message}

Provide response in JSON:
{{
    "error_type": "TypeError",
    "root_cause": "description of root cause",
    "suggested_fix": "description of the fix",
    "fixable": true
}}"""
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return ErrorAnalysis(**data)
        except Exception as e:
            return ErrorAnalysis("Unknown", f"Parse error: {e}", "Review manually", False)
