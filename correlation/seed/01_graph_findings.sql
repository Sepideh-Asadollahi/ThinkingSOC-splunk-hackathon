CREATE TABLE IF NOT EXISTS graph_findings (
    id UUID PRIMARY KEY,
    finding_type VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_score INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    ticket_status VARCHAR(32) NOT NULL DEFAULT 'open',
    owner VARCHAR(128) NOT NULL DEFAULT 'unassigned',
    display_id VARCHAR(32),
    agent_validation_status VARCHAR(64),
    content_hash VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_graph_findings_type ON graph_findings (finding_type);
CREATE INDEX IF NOT EXISTS idx_graph_findings_risk ON graph_findings (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_graph_findings_content_hash ON graph_findings (content_hash);
