"""3D Prompt Vector Projection + Centroid Distribution Drift Engine.

Two separate responsibilities:
  VectorProjectionEngine — TF-IDF → TruncatedSVD(3) → (X, Y, Z)
  DriftAnalysisEngine    — baseline vs current centroid shift → normalized drift score

Critical requirement: TF-IDF/SVD is fit on the COMBINED baseline+current corpus
so both windows share the same vector space.

drift_score = 1 - exp(-centroid_shift_distance)  → bounded to [0, 1)

Minimum data thresholds:
  baseline < 30 traces → drift_status: "insufficient_data"
  current  < 10 traces → drift_status: "insufficient_data"
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class VectorPoint:
    """3D projected point for a single trace."""
    trace_id: str
    x: float
    y: float
    z: float
    risk_level: str = "LOW"     # from existing security scanner
    threat_score: float = 0.0   # from existing security scanner
    # NOTE: is_anomaly intentionally omitted.
    # Individual point threat classification is provided via risk_level / threat_score
    # from the security scanner. Adding a second undocumented anomaly algorithm here
    # would create conflicting signals.


@dataclass
class DriftMetrics:
    """Baseline vs current distribution shift."""
    baseline_centroid: list[float] = field(default_factory=list)
    current_centroid: list[float] = field(default_factory=list)
    centroid_shift_distance: float = 0.0   # raw Euclidean distance (can exceed 1)
    drift_score: float = 0.0               # normalized: 1 - exp(-distance) ∈ [0, 1)
    drift_status: str = "ok"               # "ok" | "moderate_drift" | "significant_drift" | "insufficient_data"
    baseline_count: int = 0
    current_count: int = 0


@dataclass
class VectorDriftResult:
    points: list[VectorPoint] = field(default_factory=list)
    drift_metrics: DriftMetrics = field(default_factory=DriftMetrics)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MIN_BASELINE = 30
MIN_CURRENT = 10

DRIFT_MODERATE_THRESHOLD = 0.35
DRIFT_SIGNIFICANT_THRESHOLD = 0.60


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------

class VectorProjectionEngine:
    """Fits TF-IDF + TruncatedSVD on the combined corpus and transforms all traces."""

    def __init__(self, n_components: int = 3) -> None:
        self.n_components = n_components
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._svd: Optional[TruncatedSVD] = None

    def fit_transform(self, texts: list[str]) -> np.ndarray:
        """Fit on corpus and return (n_traces, 3) coordinate array."""
        if len(texts) < 2:
            # Return zero coords for trivially small corpora
            return np.zeros((len(texts), self.n_components))

        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            sublinear_tf=True,
            min_df=1,
        )
        tfidf_matrix = self._vectorizer.fit_transform(texts)

        n_comp = min(self.n_components, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        n_comp = max(n_comp, 1)

        self._svd = TruncatedSVD(n_components=n_comp, random_state=42)
        coords = self._svd.fit_transform(tfidf_matrix)

        # Pad to exactly 3 columns if SVD produced fewer components
        if coords.shape[1] < 3:
            pad = np.zeros((coords.shape[0], 3 - coords.shape[1]))
            coords = np.concatenate([coords, pad], axis=1)

        return coords


class DriftAnalysisEngine:
    """Computes centroid shift between baseline and current windows.

    IMPORTANT: Both windows must be transformed using the SAME fitted
    VectorProjectionEngine so coordinates are in the same space.
    """

    def compute(
        self,
        baseline_coords: np.ndarray,
        current_coords: np.ndarray,
    ) -> DriftMetrics:
        b_count = len(baseline_coords)
        c_count = len(current_coords)

        if b_count < MIN_BASELINE or c_count < MIN_CURRENT:
            return DriftMetrics(
                baseline_count=b_count,
                current_count=c_count,
                drift_status="insufficient_data",
            )

        b_centroid = baseline_coords.mean(axis=0)
        c_centroid = current_coords.mean(axis=0)

        raw_distance = float(np.linalg.norm(c_centroid - b_centroid))

        # Normalize: 1 - exp(-distance) → bounded to [0, 1)
        normalized_score = 1.0 - math.exp(-raw_distance)

        if normalized_score >= DRIFT_SIGNIFICANT_THRESHOLD:
            status = "significant_drift"
        elif normalized_score >= DRIFT_MODERATE_THRESHOLD:
            status = "moderate_drift"
        else:
            status = "ok"

        return DriftMetrics(
            baseline_centroid=[round(float(v), 6) for v in b_centroid],
            current_centroid=[round(float(v), 6) for v in c_centroid],
            centroid_shift_distance=round(raw_distance, 6),
            drift_score=round(normalized_score, 6),
            drift_status=status,
            baseline_count=b_count,
            current_count=c_count,
        )


# ---------------------------------------------------------------------------
# Top-level convenience function
# ---------------------------------------------------------------------------

def compute_vector_drift(
    traces: list[dict],
    baseline_count: int = 100,
    current_count: int = 20,
) -> VectorDriftResult:
    """
    Args:
        traces: List of dicts with keys: trace_id, prompt_text, risk_level, threat_score.
                Must be sorted oldest-first.
        baseline_count: Number of oldest traces used as baseline window.
        current_count: Number of newest traces used as current window.

    Returns:
        VectorDriftResult with 3D projected points and drift metrics.
    """
    if not traces:
        return VectorDriftResult()

    texts = [t.get("prompt_text", "") or "" for t in traces]

    # Fit on COMBINED corpus (critical: shared vector space)
    projection_engine = VectorProjectionEngine(n_components=3)
    all_coords = projection_engine.fit_transform(texts)

    # Build VectorPoint list
    points: list[VectorPoint] = []
    for i, trace in enumerate(traces):
        coord = all_coords[i]
        points.append(VectorPoint(
            trace_id=trace.get("trace_id", f"trace-{i}"),
            x=round(float(coord[0]), 6),
            y=round(float(coord[1]), 6),
            z=round(float(coord[2]), 6),
            risk_level=trace.get("risk_level", "LOW"),
            threat_score=float(trace.get("threat_score", 0.0)),
        ))

    # Split baseline and current windows from the combined-space coordinates
    total = len(traces)
    baseline_coords = all_coords[:min(baseline_count, total)]
    current_coords = all_coords[max(0, total - current_count):]

    drift_engine = DriftAnalysisEngine()
    drift_metrics = drift_engine.compute(baseline_coords, current_coords)

    return VectorDriftResult(points=points, drift_metrics=drift_metrics)
