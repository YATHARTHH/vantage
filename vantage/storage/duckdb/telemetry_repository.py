import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import duckdb

from vantage.core.logging import get_logger
from vantage.domain.events import (
    TelemetryEnvelope,
    SpanIdentity,
    SourceTool,
    EventStatus,
    LLMCallData,
    AgentRunData,
    ToolCallData,
    ChainRunData,
    BuildData,
    DeployData,
    TestRunData,
    UnclassifiedData,
)
from vantage.storage.base import AbstractTelemetryRepository

logger = get_logger(__name__)


class DuckDBTelemetryRepository(AbstractTelemetryRepository):
    """
    DuckDB OLAP repository. Runs connection operations in thread pool
    because DuckDB Python API is synchronous.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = asyncio.Lock()

    async def _get_conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            db_path_str = str(self._db_path)
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await asyncio.to_thread(
                duckdb.connect, db_path_str, read_only=False
            )
            await self._init_schema()
        return self._conn

    async def _init_schema(self) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        sql = schema_path.read_text()
        conn = self._conn
        await asyncio.to_thread(conn.execute, sql)
        migrations = [
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_scanned BOOLEAN DEFAULT FALSE",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_is_threat BOOLEAN DEFAULT FALSE",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_risk_level VARCHAR",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_threat_types VARCHAR",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_score DOUBLE",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_matched_rules VARCHAR",
            "ALTER TABLE telemetry_spans ADD COLUMN IF NOT EXISTS security_scanner_version VARCHAR",
        ]
        for m in migrations:
            try:
                await asyncio.to_thread(conn.execute, m)
            except Exception:
                pass

    def _envelope_to_row(self, env: TelemetryEnvelope) -> tuple:
        ext_id = env.external_event_id or f"{env.span.trace_id}:{env.span.span_id}"
        payload = env.payload

        model_name = getattr(payload, "model_name", None)
        model_provider = getattr(payload, "model_provider", None)
        tokens_input = getattr(payload, "tokens_input", None)
        tokens_output = getattr(payload, "tokens_output", None)
        cost_usd = getattr(payload, "cost_usd", None)

        repo_name = getattr(payload, "repo_name", None)
        branch = getattr(payload, "branch", None)
        commit_sha = getattr(payload, "commit_sha", None)
        pipeline_name = getattr(payload, "pipeline_name", None)

        sec = env.security
        if isinstance(sec, dict):
            sec_scanned = sec.get("scanned", False)
            sec_is_threat = sec.get("is_threat", False)
            sec_risk_level = str(sec.get("risk_level")) if sec.get("risk_level") else None
            sec_threat_types = json.dumps(sec.get("threat_types", [])) if sec.get("threat_types") else None
            sec_score = sec.get("threat_score")
            sec_matched_rules = json.dumps(sec.get("matched_rules", [])) if sec.get("matched_rules") else None
            sec_scanner_version = sec.get("scanner_version")
        elif sec:
            sec_scanned = sec.scanned
            sec_is_threat = sec.is_threat
            sec_risk_level = str(sec.risk_level) if sec.risk_level else None
            sec_threat_types = json.dumps([str(t) for t in sec.threat_types]) if sec.threat_types else None
            sec_score = sec.threat_score
            sec_matched_rules = json.dumps(sec.matched_rules) if sec.matched_rules else None
            sec_scanner_version = sec.scanner_version
        else:
            sec_scanned, sec_is_threat, sec_risk_level, sec_threat_types, sec_score, sec_matched_rules, sec_scanner_version = False, False, None, None, None, None, None

        return (
            str(env.event_id),
            env.project_id,
            env.source_tool.value if isinstance(env.source_tool, SourceTool) else str(env.source_tool),
            env.span.trace_id,
            env.span.span_id,
            env.span.parent_span_id,
            env.span.source_trace_id,
            env.span.source_span_id,
            ext_id,
            env.event_kind,
            env.started_at,
            env.ended_at,
            env.duration_ms,
            env.status.value if isinstance(env.status, EventStatus) else str(env.status),
            env.error_message,
            env.error_type,
            model_name,
            model_provider,
            tokens_input,
            tokens_output,
            cost_usd,
            repo_name,
            branch,
            commit_sha,
            pipeline_name,
            env.environment,
            env.owner_team,
            json.dumps(env.tags),
            sec_scanned,
            sec_is_threat,
            sec_risk_level,
            sec_threat_types,
            sec_score,
            sec_matched_rules,
            sec_scanner_version,
        )

    async def insert(self, envelope: TelemetryEnvelope) -> bool:
        async with self._lock:
            conn = await self._get_conn()
            row = self._envelope_to_row(envelope)
            res = await asyncio.to_thread(
                conn.execute,
                """
                INSERT INTO telemetry_spans (
                    event_id, project_id, source_tool, trace_id, span_id, parent_span_id,
                    source_trace_id, source_span_id, external_event_id, event_kind,
                    started_at, ended_at, duration_ms, status, error_message, error_type,
                    model_name, model_provider, tokens_input, tokens_output, cost_usd,
                    repo_name, branch, commit_sha, pipeline_name, environment, owner_team, tags,
                    security_scanned, security_is_threat, security_risk_level, security_threat_types,
                    security_score, security_matched_rules, security_scanner_version
                ) VALUES (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
                ON CONFLICT (source_tool, external_event_id)
                DO NOTHING
                RETURNING event_id
                """,
                row,
            )
            rows = await asyncio.to_thread(res.fetchall)
            return len(rows) > 0

    async def insert_batch(self, envelopes: list[TelemetryEnvelope]) -> dict:
        stored = 0
        deduped = 0
        for env in envelopes:
            ok = await self.insert(env)
            if ok:
                stored += 1
            else:
                deduped += 1
        return {"stored": stored, "deduplicated": deduped}

    async def query_metrics(
        self,
        project_id: str | None,
        from_dt: datetime,
        to_dt: datetime,
        group_by: list[str] | None = None,
    ) -> list[dict]:
        async with self._lock:
            conn = await self._get_conn()
            where_clauses = ["started_at >= ?", "started_at <= ?"]
            params: list[object] = [from_dt, to_dt]

            if project_id:
                where_clauses.append("project_id = ?")
                params.append(project_id)

            where_str = " WHERE " + " AND ".join(where_clauses)
            groups = group_by or ["project_id", "event_kind"]
            group_str = ", ".join(groups)

            sql = f"""
                SELECT
                    {group_str},
                    COUNT(*) AS total_events,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count,
                    SUM(COALESCE(cost_usd, 0.0)) AS total_cost_usd,
                    SUM(COALESCE(tokens_input, 0) + COALESCE(tokens_output, 0)) AS total_tokens,
                    AVG(duration_ms) AS avg_duration_ms,
                    QUANTILE_CONT(duration_ms, 0.5) AS p50_duration_ms,
                    QUANTILE_CONT(duration_ms, 0.95) AS p95_duration_ms
                FROM telemetry_spans
                {where_str}
                GROUP BY {group_str}
            """
            res = await asyncio.to_thread(conn.execute, sql, params)
            cols = [desc[0] for desc in res.description]
            rows = await asyncio.to_thread(res.fetchall)
            return [dict(zip(cols, row)) for row in rows]

    async def query_spans(
        self,
        project_id: str | None = None,
        trace_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        async with self._lock:
            conn = await self._get_conn()
            where_clauses = []
            params: list[object] = []

            if project_id:
                where_clauses.append("project_id = ?")
                params.append(project_id)
            if trace_id:
                where_clauses.append("trace_id = ?")
                params.append(trace_id)

            where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            sql = f"""
                SELECT * FROM telemetry_spans
                {where_str}
                ORDER BY started_at DESC
                LIMIT ?
            """
            params.append(limit)
            res = await asyncio.to_thread(conn.execute, sql, params)
            cols = [desc[0] for desc in res.description]
            rows = await asyncio.to_thread(res.fetchall)
            return [dict(zip(cols, row)) for row in rows]

    async def get_rolling_stats(
        self,
        project_id: str,
        metric: str,
        window_days: int = 7,
    ) -> dict:
        async with self._lock:
            conn = await self._get_conn()
            cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

            column_map = {
                "cost_usd": "cost_usd",
                "duration_ms": "duration_ms",
            }
            col = column_map.get(metric, metric)

            sql = f"""
                SELECT
                    AVG({col}) AS mean_val,
                    STDDEV_SAMP({col}) AS std_val
                FROM telemetry_spans
                WHERE project_id = ?
                  AND started_at >= ?
                  AND {col} IS NOT NULL
            """
            res = await asyncio.to_thread(conn.execute, sql, [project_id, cutoff])
            row = (await asyncio.to_thread(res.fetchone)) or (None, None)
            mean_val, std_val = row[0], row[1]

            curr_sql = f"""
                SELECT {col}
                FROM telemetry_spans
                WHERE project_id = ?
                  AND {col} IS NOT NULL
                ORDER BY started_at DESC
                LIMIT 1
            """
            curr_res = await asyncio.to_thread(conn.execute, curr_sql, [project_id])
            curr_row = await asyncio.to_thread(curr_res.fetchone)
            current_val = curr_row[0] if curr_row else None

            return {
                "mean": float(mean_val) if mean_val is not None else None,
                "std": float(std_val) if std_val is not None else None,
                "current": float(current_val) if current_val is not None else None,
            }

    async def get_error_rate(
        self,
        project_id: str,
        window_hours: int = 1,
    ) -> dict:
        async with self._lock:
            conn = await self._get_conn()
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

            sql = """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count
                FROM telemetry_spans
                WHERE project_id = ?
                  AND started_at >= ?
            """
            res = await asyncio.to_thread(conn.execute, sql, [project_id, cutoff])
            row = (await asyncio.to_thread(res.fetchone)) or (0, 0)
            total, errors = row[0] or 0, row[1] or 0
            rate = (errors / total * 100.0) if total > 0 else 0.0

            return {
                "total_count": total,
                "error_count": errors,
                "error_rate_pct": float(rate),
            }

    async def get_volume_stats(
        self,
        project_id: str,
        window_days: int = 7,
    ) -> dict:
        async with self._lock:
            conn = await self._get_conn()
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=window_days)
            one_hour_ago = now - timedelta(hours=1)

            baseline_sql = """
                SELECT COUNT(*) / (24.0 * ?) AS hourly_mean
                FROM telemetry_spans
                WHERE project_id = ?
                  AND started_at >= ?
            """
            b_res = await asyncio.to_thread(
                conn.execute, baseline_sql, [window_days, project_id, cutoff]
            )
            b_row = await asyncio.to_thread(b_res.fetchone)
            hourly_mean = b_row[0] if b_row and b_row[0] is not None else 0.0

            curr_sql = """
                SELECT COUNT(*)
                FROM telemetry_spans
                WHERE project_id = ?
                  AND started_at >= ?
            """
            c_res = await asyncio.to_thread(
                conn.execute, curr_sql, [project_id, one_hour_ago]
            )
            c_row = await asyncio.to_thread(c_res.fetchone)
            current_hour_count = c_row[0] if c_row else 0

            return {
                "hourly_mean": float(hourly_mean),
                "current_hour_count": int(current_hour_count),
            }

    async def list_active_project_ids(self) -> list[str]:
        async with self._lock:
            conn = await self._get_conn()
            sql = "SELECT DISTINCT project_id FROM telemetry_spans WHERE project_id != '__unmapped__'"
            res = await asyncio.to_thread(conn.execute, sql)
            rows = await asyncio.to_thread(res.fetchall)
            return [row[0] for row in rows]

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                await asyncio.to_thread(self._conn.close)
                self._conn = None
