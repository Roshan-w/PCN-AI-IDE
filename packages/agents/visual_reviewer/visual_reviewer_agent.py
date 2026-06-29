# packages/agents/visual_reviewer/visual_reviewer_agent.py
from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class Viewport:
    name: str
    width: int
    height: int

@dataclass
class VisualFinding:
    severity: str
    category: str
    description: str
    location: Optional[str]
    recommendation: str

@dataclass
class VisualReviewResult:
    approved: bool
    findings: List[VisualFinding]
    screenshots: Dict[str, bytes]
    diff_images: Optional[Dict[str, bytes]] = None

class VisualReviewerAgent:
    DEFAULT_VIEWPORTS = [
        Viewport("desktop", 1920, 1080),
        Viewport("tablet", 768, 1024),
        Viewport("mobile", 375, 812),
    ]

    def __init__(
        self,
        llm_client,
        playwright_client,
        baseline_dir = None
    ):
        self.llm = llm_client
        self.playwright = playwright_client
        self.baseline_dir = baseline_dir

    async def review(
        self,
        url: str,
        viewports: Optional[List[Viewport]] = None
    ) -> VisualReviewResult:
        return VisualReviewResult(True, [], {})
