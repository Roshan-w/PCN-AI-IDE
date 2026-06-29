import asyncio
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from operator import add
from dataclasses import dataclass
from enum import Enum
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class AgentRole(str, Enum):
    PLANNER = "planner"
    CODER = "coder"
    AUDITOR = "auditor"
    VISUAL_REVIEWER = "visual_reviewer"

@dataclass
class SubTask:
    id: str
    description: str
    assigned_agent: AgentRole
    dependencies: List[str]
    status: str
    result: Optional[str] = None

@dataclass
class CodeArtifact:
    path: str
    language: str
    content: str
    diff: str
    approved: bool = False

class WorkflowState(TypedDict):
    task_id: str
    prompt: str
    project_id: str
    mode: str
    context_files: List[str]
    repository_context: Dict[str, Any]
    rag_results: List[Dict[str, Any]]
    subtasks: List[SubTask]
    current_subtask_idx: int
    artifacts: Annotated[List[CodeArtifact], add]
    sandbox_results: List[Dict[str, Any]]
    audit_results: List[Dict[str, Any]]
    visual_review_results: List[Dict[str, Any]]
    evidence_bundle: List[Dict[str, Any]]
    retry_count: int
    max_retries: int
    status: str
    error: Optional[str]

# ============================================================================
# Node Functions (Wrapping Agents)
# ============================================================================
async def planner_agent_node(state: WorkflowState) -> WorkflowState:
    from packages.agents.planner.planner_agent import PlannerAgent
    agent = PlannerAgent()
    try:
        decomp = await agent.decompose(state["prompt"], state["repository_context"])
        state["subtasks"] = decomp.subtasks
        state["status"] = "planning_completed"
    except Exception as e:
        state["error"] = str(e)
        state["status"] = "failed"
    return state

async def context_retriever_node(state: WorkflowState) -> WorkflowState:
    state["rag_results"] = []
    return state

async def coder_agent_node(state: WorkflowState) -> WorkflowState:
    from packages.agents.coder.coder_agent import CoderAgent
    agent = CoderAgent()
    try:
        # Assuming we just process the first subtask for simplicity in this node logic,
        # or we concatenate all subtasks into one request.
        if state["subtasks"]:
            subtask = state["subtasks"][0]
        else:
            subtask = SubTask("main", state["prompt"], AgentRole.CODER, [], "queued")

        res = await agent.generate(subtask, state["repository_context"], state["rag_results"])

        # In a real langgraph reducer with `add`, returning a list appends it.
        # But we must update the state dict.
        state["artifacts"] = res.files
        state["status"] = "coding_completed"
    except Exception as e:
        state["error"] = str(e)
        state["status"] = "failed"
    return state

async def sandbox_runner_node(state: WorkflowState) -> WorkflowState:
    from packages.sandbox.runner.bubblewrap_runner import BubblewrapSandbox, SandboxConfig, Language
    runner = BubblewrapSandbox(SandboxConfig())

    results = []
    for artifact in state.get("artifacts", []):
        if artifact.language == "python":
            res = await runner.execute(artifact.content, Language.PYTHON)
            results.append({"file": artifact.path, "exit_code": res.exit_code, "output": res.stdout, "error": res.stderr})

    state["sandbox_results"] = results
    return state

async def auditor_agent_node(state: WorkflowState) -> WorkflowState:
    from packages.agents.auditor.auditor_agent import AuditorAgent
    agent = AuditorAgent()
    try:
        res = await agent.audit(state.get("artifacts", []), state.get("repository_context", {}))
        state["audit_results"] = [{"approved": res.approved, "fixable": res.fixable, "summary": res.summary}]
    except Exception as e:
        state["error"] = str(e)
        state["audit_results"] = [{"approved": False, "fixable": False, "summary": str(e)}]
    return state

async def visual_reviewer_agent_node(state: WorkflowState) -> WorkflowState:
    from packages.agents.visual_reviewer.visual_reviewer_agent import VisualReviewerAgent
    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            agent = VisualReviewerAgent(p)
            res = await agent.review("http://localhost:3000") # Assume preview server is running
            state["visual_review_results"] = [{"approved": res.approved}]
    except Exception as e:
        state["error"] = str(e)
        state["visual_review_results"] = [{"approved": False}]

    return state

async def result_aggregator_node(state: WorkflowState) -> WorkflowState:
    state["status"] = "aggregated"
    return state

async def evidence_builder_node(state: WorkflowState) -> WorkflowState:
    state["status"] = "completed"
    return state

# ============================================================================
# Decision Functions
# ============================================================================
def is_ui_file(path: str) -> bool:
    return path.endswith(".tsx") or path.endswith(".jsx") or path.endswith(".html")

def sandbox_decision(state: WorkflowState) -> str:
    if not state.get("sandbox_results"): return "escalate"
    last_result = state["sandbox_results"][-1]
    if last_result.get("exit_code") == 0:
        return "success"
    elif state.get("retry_count", 0) < state.get("max_retries", 3):
        return "retry"
    return "escalate"

def audit_decision(state: WorkflowState) -> str:
    if not state.get("audit_results"): return "blocked"
    last_audit = state["audit_results"][-1]
    if last_audit.get("approved"):
        return "approved"
    elif last_audit.get("fixable") and state.get("retry_count", 0) < state.get("max_retries", 3):
        return "needs_fixes"
    return "blocked"

def visual_review_decision(state: WorkflowState) -> str:
    has_ui_artifacts = any(is_ui_file(a.path) for a in state.get("artifacts", []))
    return "continue" if has_ui_artifacts else "skip"

# ============================================================================
# Workflow Definition
# ============================================================================
def create_coding_workflow():
    workflow = StateGraph(WorkflowState)

    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("context_retriever", context_retriever_node)
    workflow.add_node("coder", coder_agent_node)
    workflow.add_node("sandbox", sandbox_runner_node)
    workflow.add_node("auditor", auditor_agent_node)
    workflow.add_node("visual_reviewer", visual_reviewer_agent_node)
    workflow.add_node("aggregator", result_aggregator_node)
    workflow.add_node("evidence_builder", evidence_builder_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "context_retriever")
    workflow.add_edge("context_retriever", "coder")
    workflow.add_edge("coder", "sandbox")

    workflow.add_conditional_edges(
        "sandbox",
        sandbox_decision,
        {
            "success": "auditor",
            "retry": "coder",
            "escalate": "aggregator"
        }
    )

    workflow.add_conditional_edges(
        "auditor",
        audit_decision,
        {
            "approved": "visual_reviewer",
            "needs_fixes": "coder",
            "blocked": "aggregator"
        }
    )

    workflow.add_conditional_edges(
        "visual_reviewer",
        visual_review_decision,
        {
            "continue": "aggregator",
            "skip": "aggregator"
        }
    )

    workflow.add_edge("aggregator", "evidence_builder")
    workflow.add_edge("evidence_builder", END)

    return workflow.compile(checkpointer=MemorySaver())
