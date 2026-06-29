import pytest
import importlib.util
import sys

def test_imports():
    from packages.shared.models.entities import Task, TaskMode, TaskStatus
    from packages.api.gateway.main import app, TaskSubmission
    from packages.orchestrator.workflows.coding_workflow import WorkflowState, SubTask
    from packages.agents.planner.planner_agent import PlannerAgent
    from packages.agents.coder.coder_agent import CoderAgent
    from packages.agents.auditor.auditor_agent import AuditorAgent
    from packages.agents.visual_reviewer.visual_reviewer_agent import VisualReviewerAgent
    from packages.sandbox.runner.bubblewrap_runner import BubblewrapSandbox
    from packages.orchestrator.agents.self_repair import SelfRepairingCodeLoop
    from packages.orchestrator.router.task_router import TaskRouter

    spec = importlib.util.spec_from_file_location("server_config", "packages/inference-server/config/server_config.py")
    server_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_config)
    assert server_config.vLLMServerConfig

def test_entities():
    from packages.shared.models.entities import Task, TaskMode, TaskStatus
    task = Task()
    assert task.mode == TaskMode.SAFE
    assert task.status == TaskStatus.QUEUED
