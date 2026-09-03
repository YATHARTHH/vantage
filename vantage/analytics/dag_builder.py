"""Multi-Agent DAG Topology Builder.

Constructs directed execution graphs from OpenTelemetry & Vantage telemetry span trees.
Includes safeguards against malformed spans, cycle protection, orphan span collection under synthetic roots,
retry attempt metadata, and summary metric aggregations.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class DAGNode:
    """Single node in an agent execution graph representing an agent run, LLM call, or tool call."""
    id: str
    parent_id: Optional[str]
    type: str          # "agent_run" | "llm_call" | "tool_execution" | "synthetic_root"
    name: str          # model_name or source_tool
    depth: int = 0
    duration_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    status: str = "success"        # "success" | "error" | "running" | "blocked"
    is_retry: bool = False
    attempt_number: int = 1
    retry_group_id: Optional[str] = None
    has_payload: bool = False      # Lightweight capability signal for lazy UI payload fetching
    children: list[str] = field(default_factory=list)


@dataclass
class DAGEdge:
    """Directed edge between parent agent/tool and child execution node."""
    source: str
    target: str
    edge_type: str = "child_execution"  # "child_execution" | "retry_loop" | "handoff"


@dataclass
class DAGSummary:
    """Aggregated graph-level summary metrics."""
    total_nodes: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_duration_ms: float = 0.0
    max_depth: int = 0
    retry_count: int = 0
    status: str = "success"  # "blocked" > "error" > "running" > "success"
    has_cycles: bool = False


@dataclass
class DAGGraph:
    """Complete multi-agent execution topology payload."""
    trace_id: str
    project_id: str
    root_node_id: str
    summary: DAGSummary = field(default_factory=DAGSummary)
    nodes: list[DAGNode] = field(default_factory=list)
    edges: list[DAGEdge] = field(default_factory=list)


def _parse_timestamp(ts_val: Any) -> Optional[datetime]:
    if not ts_val:
        return None
    if isinstance(ts_val, datetime):
        return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc)
    if isinstance(ts_val, str):
        try:
            cleaned = ts_val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def build_dag_from_spans(spans: list[dict[str, Any]], trace_id: str) -> DAGGraph:
    """
    Constructs a DAGGraph from raw telemetry span dicts.
    
    Args:
        spans: List of span dictionaries belonging to the trace.
        trace_id: Trace identifier.

    Returns:
        DAGGraph instance containing structured nodes, edges, and graph summary metrics.
    """
    if not spans:
        return DAGGraph(
            trace_id=trace_id,
            project_id="unknown",
            root_node_id="",
            summary=DAGSummary(status="success"),
        )

    project_id = spans[0].get("project_id") or "unknown"
    
    # 1. Parse timestamps & sort spans
    def get_sort_key(s: dict[str, Any]) -> float:
        dt = _parse_timestamp(s.get("started_at"))
        return dt.timestamp() if dt else 0.0

    sorted_spans = sorted(spans, key=get_sort_key)

    # 2. Build initial DAGNodes map
    node_map: dict[str, DAGNode] = {}
    valid_ids: set[str] = set()

    for s in sorted_spans:
        node_id = str(s.get("span_id") or s.get("event_id") or f"node-{len(node_map)}")
        parent_id = s.get("parent_span_id")
        if parent_id:
            parent_id = str(parent_id)

        # Self-parent protection
        if parent_id == node_id:
            parent_id = None

        valid_ids.add(node_id)
        label = s.get("model_name") or s.get("event_kind") or s.get("source_tool") or "Agent Node"
        kind = s.get("event_kind") or "agent_run"
        status = s.get("status") or "success"

        duration = float(s.get("duration_ms") or 0.0)
        tok_in = int(s.get("tokens_input") or 0)
        tok_out = int(s.get("tokens_output") or 0)
        cost = float(s.get("cost_usd") or 0.0)

        # Check payload capability signal
        tags = s.get("tags")
        has_payload = False
        if isinstance(tags, dict) and tags.get("prompt_preview"):
            has_payload = True
        elif isinstance(tags, str) and "prompt_preview" in tags:
            has_payload = True

        node_map[node_id] = DAGNode(
            id=node_id,
            parent_id=parent_id,
            type=kind,
            name=label,
            duration_ms=round(duration, 2),
            tokens_input=tok_in,
            tokens_output=tok_out,
            cost_usd=round(cost, 6),
            status=status,
            has_payload=has_payload,
        )

    # 3. Cycle Detection & Orphan Collection
    visited_global: set[str] = set()
    cycles_detected = False

    # Detect cycles via DFS
    for start_id in list(node_map.keys()):
        if start_id in visited_global:
            continue
        path: list[str] = []
        path_set: set[str] = set()
        curr: Optional[str] = start_id

        while curr and curr in node_map:
            if curr in path_set:
                # Cycle detected! Break offending link
                cycles_detected = True
                node_map[curr].parent_id = None
                break
            if curr in visited_global:
                break

            visited_global.add(curr)
            path_set.add(curr)
            path.append(curr)
            curr = node_map[curr].parent_id

    # 4. Identify Root Spans vs Orphan Spans
    root_candidates: list[DAGNode] = []
    orphan_spans: list[DAGNode] = []

    for node in node_map.values():
        if not node.parent_id or node.parent_id not in valid_ids:
            if node.parent_id and node.parent_id not in valid_ids:
                orphan_spans.append(node)
            else:
                root_candidates.append(node)

    # Handle Synthetic Root for Orphan Spans or Multiple Roots
    synthetic_root_created = False
    primary_root_id = ""

    if orphan_spans or len(root_candidates) > 1 or cycles_detected:
        synthetic_root_id = "__orphan_root__"
        synthetic_root = DAGNode(
            id=synthetic_root_id,
            parent_id=None,
            type="synthetic_root",
            name="Unattached Spans",
            status="success",
        )
        node_map[synthetic_root_id] = synthetic_root
        synthetic_root_created = True
        primary_root_id = synthetic_root_id

        # Attach orphan spans and non-primary root candidates to synthetic root
        for orphan in orphan_spans:
            orphan.parent_id = synthetic_root_id

        if len(root_candidates) > 1 or cycles_detected:
            for extra_root in root_candidates:
                extra_root.parent_id = synthetic_root_id
    elif root_candidates:
        primary_root_id = root_candidates[0].id

    # 5. Retry Attempt Semantics & Edge Building
    edges: list[DAGEdge] = []
    retry_count = 0
    seen_calls: dict[tuple[str, str], int] = {}  # (parent_id, label) -> attempt_count

    for node_id, node in list(node_map.items()):
        if node.parent_id and node.parent_id in node_map:
            parent_node = node_map[node.parent_id]
            parent_node.children.append(node_id)

            call_key = (node.parent_id, node.name)
            seen_calls[call_key] = seen_calls.get(call_key, 0) + 1
            attempt = seen_calls[call_key]

            if attempt > 1:
                node.is_retry = True
                node.attempt_number = attempt
                node.retry_group_id = f"retry-{node.parent_id}-{node.name}"
                retry_count += 1
                edges.append(DAGEdge(source=node.parent_id, target=node_id, edge_type="retry_loop"))
            else:
                node.attempt_number = 1
                edges.append(DAGEdge(source=node.parent_id, target=node_id, edge_type="child_execution"))

    # 6. Depth Calculation via BFS
    max_depth = 0
    if primary_root_id and primary_root_id in node_map:
        queue = [(primary_root_id, 0)]
        visited_bfs: set[str] = set()

        while queue:
            curr_id, depth = queue.pop(0)
            if curr_id in visited_bfs:
                continue
            visited_bfs.add(curr_id)

            if depth > max_depth:
                max_depth = depth

            if curr_id in node_map:
                node_map[curr_id].depth = depth
                for child_id in node_map[curr_id].children:
                    queue.append((child_id, depth + 1))

    # 7. Summary Aggregation
    total_cost = sum(n.cost_usd for n in node_map.values() if n.type != "synthetic_root")
    total_tokens = sum((n.tokens_input + n.tokens_output) for n in node_map.values() if n.type != "synthetic_root")

    # Overall duration: max_end - min_start
    min_start_dt: Optional[datetime] = None
    max_end_dt: Optional[datetime] = None

    for s in sorted_spans:
        s_dt = _parse_timestamp(s.get("started_at"))
        e_dt = _parse_timestamp(s.get("ended_at")) or s_dt

        if s_dt and (min_start_dt is None or s_dt < min_start_dt):
            min_start_dt = s_dt
        if e_dt and (max_end_dt is None or e_dt > max_end_dt):
            max_end_dt = e_dt

    total_duration_ms = 0.0
    if min_start_dt and max_end_dt and max_end_dt >= min_start_dt:
        total_duration_ms = round((max_end_dt - min_start_dt).total_seconds() * 1000.0, 2)
    elif sorted_spans:
        total_duration_ms = sum(n.duration_ms for n in node_map.values() if n.type != "synthetic_root")

    # Summary status precedence: blocked > error > running > success
    statuses = set(n.status for n in node_map.values() if n.type != "synthetic_root")
    if "blocked" in statuses:
        overall_status = "blocked"
    elif "error" in statuses:
        overall_status = "error"
    elif "running" in statuses:
        overall_status = "running"
    else:
        overall_status = "success"

    summary = DAGSummary(
        total_nodes=len([n for n in node_map.values() if n.type != "synthetic_root"]),
        total_cost_usd=round(total_cost, 6),
        total_tokens=total_tokens,
        total_duration_ms=round(total_duration_ms, 2),
        max_depth=max_depth,
        retry_count=retry_count,
        status=overall_status,
        has_cycles=cycles_detected,
    )

    return DAGGraph(
        trace_id=trace_id,
        project_id=project_id,
        root_node_id=primary_root_id,
        summary=summary,
        nodes=list(node_map.values()),
        edges=edges,
    )
