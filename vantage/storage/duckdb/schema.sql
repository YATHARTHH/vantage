-- DuckDB DDL schema for Vantage telemetry

CREATE TABLE IF NOT EXISTS telemetry_spans (
    event_id          VARCHAR PRIMARY KEY,
    project_id        VARCHAR NOT NULL,
    source_tool       VARCHAR NOT NULL,

    trace_id          VARCHAR NOT NULL,
    span_id           VARCHAR NOT NULL,
    parent_span_id    VARCHAR,

    source_trace_id   VARCHAR,
    source_span_id    VARCHAR,
    external_event_id VARCHAR,

    event_kind        VARCHAR NOT NULL,

    started_at        TIMESTAMPTZ NOT NULL,
    ended_at          TIMESTAMPTZ,
    duration_ms       DOUBLE,

    status            VARCHAR NOT NULL,
    error_message     VARCHAR,
    error_type        VARCHAR,

    model_name        VARCHAR,
    model_provider    VARCHAR,
    tokens_input      INTEGER,
    tokens_output     INTEGER,
    cost_usd          DOUBLE,

    repo_name         VARCHAR,
    branch            VARCHAR,
    commit_sha        VARCHAR,
    pipeline_name     VARCHAR,
    environment       VARCHAR,

    owner_team        VARCHAR,
    tags              JSON DEFAULT '{}',

    -- Security Scan Metadata
    security_scanned          BOOLEAN DEFAULT FALSE,
    security_is_threat        BOOLEAN DEFAULT FALSE,
    security_risk_level       VARCHAR,
    security_threat_types     VARCHAR,
    security_score            DOUBLE,
    security_matched_rules    VARCHAR,
    security_scanner_version  VARCHAR,

    ingested_at       TIMESTAMPTZ DEFAULT now()
);

-- Deduplication index on (source_tool, external_event_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_dedup_external
    ON telemetry_spans (source_tool, external_event_id);

CREATE INDEX IF NOT EXISTS idx_spans_project_time ON telemetry_spans (project_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_spans_trace        ON telemetry_spans (trace_id, span_id);
CREATE INDEX IF NOT EXISTS idx_spans_kind         ON telemetry_spans (event_kind, started_at DESC);

CREATE TABLE IF NOT EXISTS metrics_hourly (
    bucket_hour     TIMESTAMPTZ NOT NULL,
    project_id      VARCHAR     NOT NULL,
    event_kind      VARCHAR     NOT NULL,
    total_events    INTEGER     DEFAULT 0,
    error_count     INTEGER     DEFAULT 0,
    total_cost_usd  DOUBLE      DEFAULT 0,
    total_tokens    INTEGER     DEFAULT 0,
    avg_duration_ms DOUBLE,
    p50_duration_ms DOUBLE,
    p95_duration_ms DOUBLE,
    PRIMARY KEY (bucket_hour, project_id, event_kind)
);

CREATE TABLE IF NOT EXISTS unmapped_sources (
    source_tool       VARCHAR NOT NULL,
    source_identifier VARCHAR NOT NULL,
    first_seen_at     TIMESTAMPTZ DEFAULT now(),
    event_count       INTEGER DEFAULT 1,
    PRIMARY KEY (source_tool, source_identifier)
);
