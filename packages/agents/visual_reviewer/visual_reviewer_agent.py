import json
import base64
from dataclasses import dataclass
from typing import List, Optional, Dict
from openai import AsyncOpenAI

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
        playwright_client,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "empty",
        model: str = "qwen-vl-7b",
        baseline_dir = None
    ):
        self.llm = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.playwright = playwright_client
        self.baseline_dir = baseline_dir

    async def review(
        self,
        url: str,
        viewports: Optional[List[Viewport]] = None
    ) -> VisualReviewResult:
        viewports = viewports or self.DEFAULT_VIEWPORTS
        screenshots = {}
        findings = []

        # Real playwright screenshot logic
        browser = await self.playwright.chromium.launch()

        try:
            for viewport in viewports:
                context = await browser.new_context(
                    viewport={"width": viewport.width, "height": viewport.height}
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(1000) # Wait for animations
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshots[viewport.name] = screenshot_bytes

                await context.close()

                # Analyze with Vision LLM
                b64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                prompt = f"""Analyze this UI screenshot for issues.
URL: {url}
Viewport: {viewport.name} ({viewport.width}x{viewport.height})
Check for:
1. Layout issues
2. Accessibility issues
3. Responsive design issues
4. Content issues

Output findings in JSON format:
{{
  "findings": [
    {{
      "severity": "critical|high|medium|low",
      "category": "layout|accessibility|responsive|content",
      "description": "<issue description>",
      "location": "<approximate location on screen>",
      "recommendation": "<fix suggestion>"
    }}
  ]
}}"""
                try:
                    response = await self.llm.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}}
                                ]
                            }
                        ],
                        temperature=0.1
                    )
                    content = response.choices[0].message.content
                    # Extract JSON block
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    data = json.loads(content)
                    for item in data.get("findings", []):
                        findings.append(VisualFinding(**item))
                except Exception as e:
                    print(f"Vision LLM error: {e}")

        finally:
            await browser.close()

        approved = not any(f.severity in ["critical", "high"] for f in findings)
        return VisualReviewResult(approved=approved, findings=findings, screenshots=screenshots)
