"""Unit tests for Multi-Agent DAG Topology Builder."""
from vantage.analytics.dag_builder import build_dag_from_spans, DAGGraph


def test_basic_dag_tree_construction():
    spans = [
        {
            "span_id": "root-1",
            "parent_span_id": None,
            "project_id": "search-v2",
            "model_name": "PlannerAgent",
            "event_kind": "agent_run",
            "status": "success",
            "cost_usd": 0.01,
            "tokens_input": 100,
            "tokens_output": 50,
            "duration_ms": 500.0,
            "started_at": "2026-09-03T10:00:00Z",
            "ended_at": "2026-09-03T10:00:02Z",
        },
        {
            "span_id": "child-1",
            "parent_span_id": "root-1",
            "project_id": "search-v2",
            "model_name": "SearchTool",
            "event_kind": "tool_execution",
            "status": "success",
            "cost_usd": 0.005,
            "tokens_input": 50,
            "tokens_output": 20,
            "duration_ms": 200.0,
            "started_at": "2026-09-03T10:00:00.500Z",
            "ended_at": "2026-09-03T10:00:01.000Z",
        },
        {
            "span_id": "child-2",
            "parent_span_id": "root-1",
            "project_id": "search-v2",
            "model_name": "GPT-4o",
            "event_kind": "llm_call",
            "status": "success",
            "cost_usd": 0.02,
            "tokens_input": 400,
            "tokens_output": 150,
            "duration_ms": 800.0,
            "started_at": "2026-09-03T10:00:01.000Z",
            "ended_at": "2026-09-03T10:00:02.000Z",
        },
    ]

    graph: DAGGraph = build_dag_from_spans(spans, trace_id="trace-101")

    assert graph.trace_id == "trace-101"
    assert graph.project_id == "search-v2"
    assert graph.root_node_id == "root-1"
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.summary.total_nodes == 3
    assert graph.summary.total_tokens == 770
    assert abs(graph.summary.total_cost_usd - 0.035) < 1e-5
    assert graph.summary.max_depth == 1
    assert graph.summary.status == "success"


def test_retry_attempt_metadata():
    spans = [
        {"span_id": "p-1", "parent_span_id": None, "model_name": "AgentRoot", "started_at": "2026-09-03T10:00:00Z"},
        {"span_id": "c-1", "parent_span_id": "p-1", "model_name": "SearchTool", "started_at": "2026-09-03T10:00:01Z"},
        {"span_id": "c-2", "parent_span_id": "p-1", "model_name": "SearchTool", "started_at": "2026-09-03T10:00:02Z"},  # Retry 1
    ]

    graph = build_dag_from_spans(spans, trace_id="trace-retry")

    assert graph.summary.retry_count == 1
    c1 = next(n for n in graph.nodes if n.id == "c-1")
    c2 = next(n for n in graph.nodes if n.id == "c-2")

    assert c1.is_retry is False
    assert c1.attempt_number == 1
    assert c2.is_retry is True
    assert c2.attempt_number == 2
    assert c2.retry_group_id == "retry-p-1-SearchTool"


def test_cycle_protection_and_synthetic_root():
    # Malformed cycle: a -> b -> a
    spans = [
        {"span_id": "a", "parent_span_id": "b", "model_name": "A", "started_at": "2026-09-03T10:00:00Z"},
        {"span_id": "b", "parent_span_id": "a", "model_name": "B", "started_at": "2026-09-03T10:00:01Z"},
    ]

    graph = build_dag_from_spans(spans, trace_id="trace-cycle")

    assert graph.summary.has_cycles is True
    assert graph.root_node_id == "__orphan_root__"
    assert any(n.id == "__orphan_root__" for n in graph.nodes)
