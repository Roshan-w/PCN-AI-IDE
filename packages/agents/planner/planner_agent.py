import math
import random
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from packages.orchestrator.workflows.coding_workflow import SubTask, AgentRole
from openai import AsyncOpenAI

@dataclass
class TaskDecomposition:
    subtasks: List[SubTask]
    dependency_graph: Dict[str, List[str]]
    estimated_complexity: float
    planning_confidence: float

@dataclass
class MCTSNode:
    state: str
    parent: Optional['MCTSNode'] = None
    children: List['MCTSNode'] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0
    unexpanded_actions: List[str] = field(default_factory=list)

class PlannerAgent:
    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "empty",
        model: str = "qwen-2.5-coder-7b-instruct",
        max_subtasks: int = 10,
        mcts_iterations: int = 5,
        exploration_weight: float = 1.41
    ):
        self.llm = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.max_subtasks = max_subtasks
        self.mcts_iterations = mcts_iterations
        self.exploration_weight = exploration_weight

    async def decompose(self, prompt: str, context: Dict[str, Any]) -> TaskDecomposition:
        candidates = await self._generate_candidates(prompt, context)
        root = MCTSNode(state="initial", unexpanded_actions=candidates)

        for _ in range(self.mcts_iterations):
            node = self._select(root)
            if node.unexpanded_actions:
                node = self._expand(node)
            value = await self._simulate(node, prompt, context)
            self._backpropagate(node, value)

        if not root.children:
            return self._parse_decomposition(root.state)
        best_child = max(root.children, key=lambda n: n.value / max(n.visits, 1))
        return self._parse_decomposition(best_child.state)

    async def _generate_candidates(self, prompt: str, context: Dict[str, Any]) -> List[str]:
        system_prompt = """You are a task decomposition expert.
Break down complex coding tasks into smaller, atomic subtasks.
Rules:
- Each subtask should be completable by a single agent
- Identify dependencies between subtasks
- Keep total subtasks under 10
- Use clear, specific descriptions

Output format:
SUBTASK: <id>|<description>|DEPENDENCIES: <comma-separated ids>
"""
        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Decompose this task:\n\n{prompt}"}
            ],
            temperature=0.7
        )
        return [response.choices[0].message.content]

    def _select(self, node: MCTSNode) -> MCTSNode:
        while node.children and not node.unexpanded_actions:
            node = max(node.children, key=lambda c: self._ucb1(c))
        return node

    def _ucb1(self, node: MCTSNode) -> float:
        if node.visits == 0:
            return float('inf')
        exploitation = node.value / node.visits
        exploration = self.exploration_weight * math.sqrt(
            math.log(node.parent.visits) / node.visits
        ) if node.parent else 0
        return exploitation + exploration

    def _expand(self, node: MCTSNode) -> MCTSNode:
        action = node.unexpanded_actions.pop()
        child = MCTSNode(
            state=action,
            parent=node,
            unexpanded_actions=[]
        )
        node.children.append(child)
        return child

    async def _simulate(self, node: MCTSNode, prompt: str, context: Dict[str, Any]) -> float:
        estimation_prompt = f"""Rate this task decomposition for success probability.
Original task: {prompt}
Decomposition:
{node.state}

Rate the decomposition on Completeness, Atomicity, and Dependency correctness (0-1).
Output only a single number (0-1) representing success probability."""
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": estimation_prompt}],
                temperature=0.3
            )
            return float(response.choices[0].message.content.strip())
        except ValueError:
            return 0.5
        except Exception:
            return 0.5

    def _backpropagate(self, node: MCTSNode, value: float):
        while node:
            node.visits += 1
            node.value += value
            node = node.parent

    def _parse_decomposition(self, state: str) -> TaskDecomposition:
        subtasks = []
        deps = {}
        for line in state.split('\n'):
            if line.startswith("SUBTASK:"):
                parts = line.split('|')
                if len(parts) >= 3:
                    task_id = parts[0].replace("SUBTASK:", "").strip()
                    desc = parts[1].strip()
                    dep_str = parts[2].replace("DEPENDENCIES:", "").strip()
                    dependencies = [d.strip() for d in dep_str.split(',')] if dep_str else []

                    subtasks.append(SubTask(
                        id=task_id,
                        description=desc,
                        assigned_agent=AgentRole.CODER,
                        dependencies=dependencies,
                        status="queued"
                    ))
                    deps[task_id] = dependencies

        return TaskDecomposition(
            subtasks=subtasks,
            dependency_graph=deps,
            estimated_complexity=0.5,
            planning_confidence=0.85
        )
