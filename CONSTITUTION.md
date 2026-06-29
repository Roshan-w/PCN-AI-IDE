# PCN AI IDE Constitution
This constitution serves as the guiding document for all future development of the PCN AI IDE.

## Core Principles
1. **Privacy-First Architecture**: All inference runs locally with no external API calls.
2. **No-Docker Deployment**: Uses Bubblewrap for sandboxing and systemd for service management.
3. **Horizontal Scalability**: Supports distribution across 99 worker nodes and 1 master node in a star topology.
4. **Enterprise Security**: Strict adherence to OWASP Top 10 for LLMs compliance, end-to-end encryption, and role-based access controls.
5. **Real-Time UX**: Sub-2-second response latency for code completions via streaming WebSockets.
6. **Multi-Agent Orchestration**: Planner, Coder, Auditor, and Visual Reviewer agents working in a cohesive LangGraph workflow.
7. **Local Execution Context**: Everything operates under an air-gapped or private network model unless explicitly configured otherwise.

## Development Guidelines
- Follow the defined implementation phases and checkpoint before moving to the next.
- Adhere to the defined 4-layer architecture: IDE Client, Control Plane, Worker Plane, and Data Plane.
- Always use the predefined shared data models and API schemas.
- Ensure strict typing and comprehensive error handling for all backend Python code.
- Write thorough tests and perform proper verification at each phase.
