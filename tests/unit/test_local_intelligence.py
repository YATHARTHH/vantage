import pytest
from vantage.evaluators.quality_evaluator import LocalHeuristicEvaluator, RAGQualityResult
from vantage.cache.semantic_cache import LocalSimilarityCache, build_exact_hash
from vantage.analytics.vector_drift import compute_vector_drift, VectorProjectionEngine, DriftAnalysisEngine


def test_heuristic_evaluator_rag_supported():
    evaluator = LocalHeuristicEvaluator()
    context = [
        "Vantage is an open-source local AI observability hub created for engineering teams.",
        "It uses DuckDB as an OLAP database for sub-millisecond trace storage."
    ]
    response = "Vantage stores traces in DuckDB for AI observability."
    result = evaluator.evaluate(context, response)

    assert result.evaluated is True
    assert result.faithfulness_score > 0.0
    assert result.response_context_overlap > 0.0
    assert result.safety_heuristic == 1.0


def test_heuristic_evaluator_missing_context():
    evaluator = LocalHeuristicEvaluator()
    result = evaluator.evaluate([], "Some response")
    assert result.evaluated is False
    assert result.skip_reason != ""


def test_similarity_cache_exact_and_fuzzy():
    cache = LocalSimilarityCache()
    cache.load_entry(
        cache_id="c1",
        exact_hash=build_exact_hash("proj-1", "gpt-4o", "v1", "", "How do I setup DuckDB?"),
        project_id="proj-1",
        prompt_text="How do I setup DuckDB?",
        response_text="DuckDB can be initialized using duckdb.connect()",
        tokens_input=10,
        tokens_output=20,
        original_cost_usd=0.001,
        expires_at=None,
    )

    # 1. Exact match hit
    hit_exact = cache.get("proj-1", "gpt-4o", "v1", "", "How do I setup DuckDB?")
    assert hit_exact is not None
    assert hit_exact.hit_type == "exact"
    assert hit_exact.similarity == 1.0

    # 2. Fuzzy match hit (>= 0.88 similarity)
    hit_fuzzy = cache.get("proj-1", "gpt-4o", "v1", "", "How do I setup DuckDB database?")
    assert hit_fuzzy is not None
    assert hit_fuzzy.hit_type in ("exact", "fuzzy")

    # 3. Cache miss (< 0.88 similarity)
    hit_miss = cache.get("proj-1", "gpt-4o", "v1", "", "What is the capital of France?")
    assert hit_miss is None


def test_vector_drift_engine():
    traces = []
    # Baseline traces: about DuckDB & SQL
    for i in range(35):
        traces.append({
            "trace_id": f"t-{i}",
            "prompt_text": f"Query DuckDB SQL telemetry database trace {i}",
            "risk_level": "LOW",
            "threat_score": 0.0,
        })
    # Current traces: shifted domain to Kubernetes deployment
    for i in range(35, 50):
        traces.append({
            "trace_id": f"t-{i}",
            "prompt_text": f"Deploy Kubernetes cluster helm chart pods service container {i}",
            "risk_level": "MEDIUM",
            "threat_score": 0.3,
        })

    result = compute_vector_drift(traces, baseline_count=30, current_count=10)

    assert len(result.points) == 50
    assert result.drift_metrics.baseline_count == 30
    assert result.drift_metrics.current_count == 10
    assert result.drift_metrics.centroid_shift_distance > 0.0
    assert 0.0 <= result.drift_metrics.drift_score < 1.0
    assert result.drift_metrics.drift_status in ("moderate_drift", "significant_drift")
