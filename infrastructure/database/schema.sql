-- packages/infrastructure/database/schema.sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- Users and Projects
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    api_key_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    repository_url VARCHAR(1024),
    design_protocol VARCHAR(50) DEFAULT 'tailwind_shadcn',
    default_mode VARCHAR(20) DEFAULT 'safe',
    owner_id UUID REFERENCES users(id),
    qdrant_collection VARCHAR(255),
    indexing_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE project_members (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'developer',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

-- ============================================================================
-- Tasks
-- ============================================================================
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id),
    user_id UUID REFERENCES users(id),
    -- Input
    prompt TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    options JSONB DEFAULT '{}',
    mode VARCHAR(20) DEFAULT 'safe',
    -- State
    status VARCHAR(20) DEFAULT 'queued',
    progress FLOAT DEFAULT 0.0,
    current_stage VARCHAR(100),
    -- Decomposition (stored in JSONB for flexibility)
    subtasks JSONB DEFAULT '[]',
    current_subtask_idx INTEGER DEFAULT 0,
    -- Routing
    assigned_workers TEXT[] DEFAULT '{}',
    model_used VARCHAR(100),
    -- Metrics
    tokens_generated INTEGER DEFAULT 0,
    inference_time_ms INTEGER DEFAULT 0,
    total_time_ms INTEGER DEFAULT 0,
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    -- Indexes for common queries
    CONSTRAINT valid_status CHECK (
        status IN ('queued', 'planning', 'executing', 'reviewing',
                   'completed', 'failed', 'cancelled')
    )
);

-- Indexes
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_user ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created ON tasks(created_at DESC);

-- Full-text search on prompts
CREATE INDEX idx_tasks_prompt_search ON tasks USING GIN (to_tsvector('english', prompt));

-- ============================================================================
-- Code Artifacts
-- ============================================================================
CREATE TABLE code_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    subtask_id UUID,
    path VARCHAR(1024) NOT NULL,
    language VARCHAR(50),
    action VARCHAR(20) DEFAULT 'create',
    -- Content stored in separate object storage
    content_ref VARCHAR(255),
    original_content_ref VARCHAR(255),
    diff TEXT,
    -- Approval
    approved BOOLEAN DEFAULT false,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    -- Audit
    security_reviewed BOOLEAN DEFAULT false,
    quality_reviewed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_artifacts_task ON code_artifacts(task_id);
CREATE INDEX idx_artifacts_path ON code_artifacts(path);

-- ============================================================================
-- Evidence Bundles
-- ============================================================================
CREATE TABLE evidence_bundles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    total_tokens INTEGER DEFAULT 0,
    total_duration_ms INTEGER DEFAULT 0,
    agents_involved TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    exported_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE evidence_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bundle_id UUID REFERENCES evidence_bundles(id) ON DELETE CASCADE,
    agent VARCHAR(100) NOT NULL,
    action VARCHAR(255),
    reasoning TEXT,
    input_snapshot TEXT,
    output_snapshot TEXT,
    model_used VARCHAR(100),
    tokens_used INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_evidence_bundle ON evidence_entries(bundle_id);

-- ============================================================================
-- Workers
-- ============================================================================
CREATE TABLE workers (
    id VARCHAR(100) PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL,
    ip_address INET NOT NULL,
    status VARCHAR(20) DEFAULT 'offline',
    max_concurrent_tasks INTEGER DEFAULT 4,
    current_tasks INTEGER DEFAULT 0,
    gpu_model VARCHAR(100),
    gpu_memory_mb INTEGER,
    system_memory_mb INTEGER,
    loaded_models TEXT[] DEFAULT '{}',
    available_models TEXT[] DEFAULT '{}',
    gpu_utilization FLOAT DEFAULT 0.0,
    memory_utilization FLOAT DEFAULT 0.0,

    last_heartbeat TIMESTAMP WITH TIME ZONE,
    error_count INTEGER DEFAULT 0,

    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_workers_status ON workers(status);
CREATE INDEX idx_workers_heartbeat ON workers(last_heartbeat);

-- ============================================================================
-- Audit Log
-- ============================================================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
