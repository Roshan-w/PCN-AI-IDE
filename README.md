# PCN AI IDE (Private Cluster Network AI Integrated Development Environment)

PCN AI IDE is an autonomous distributed AI coding environment designed for enterprise software engineering teams. This self-hosted system leverages a cluster of 100 personal computers arranged in a star topology (one master node, 99 worker nodes), all running Ubuntu Server 24.04 LTS.

## Key Features
- **Local Inference**: Data privacy and control over AI-powered workflows.
- **No-Docker Deployment**: Leverages Bubblewrap for sandboxing.
- **Multi-Agent Architecture**: Uses LangGraph to orchestrate Planner, Coder, Auditor, and Visual Reviewer agents.
- **Enterprise Security**: Adherence to OWASP Top 10 for LLMs compliance.
- **Fast Performance**: Sub-2-second response latency for code completions.

## Repository Structure
- `packages/`
  - `inference-server/`: vLLM model serving configuration
  - `orchestrator/`: LangGraph workflow engine and Celery task routing
  - `sandbox/`: Bubblewrap secure code execution runner
  - `vscode-extension/`: IDE Client interface
  - `agents/`: Implementations for Planner, Coder, Auditor, Visual Reviewer
  - `api/`: FastAPI Gateway and REST/WebSocket endpoints
  - `shared/`: Common utilities and entities
- `infrastructure/`
  - `ansible/`: Fleet provisioning playbooks
  - `database/`: Schema and migration files
- `docs/`: Comprehensive requirements, design, and planning documents
- `benchmarks/`: Evaluation and performance testing suites
