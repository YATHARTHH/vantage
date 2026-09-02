"""Local Heuristic Faithfulness Evaluator for RAG traces.

Framed as a heuristic approximation, not a ground-truth hallucination detector.
Evaluates only spans carrying explicit RAG context (vantage.rag.context).
Returns separate, independently interpretable signals.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Result dataclass — all signals stored independently
# ---------------------------------------------------------------------------

@dataclass
class RAGQualityResult:
    """Separate heuristic signals for a single RAG trace evaluation."""

    faithfulness_score: float = 0.0
    """n-gram overlap: supported response claims / total response claims.
    Measures 'Did the response make claims supported by the context?'
    NOT 'How much of the context appeared in the response?'
    """

    unsupported_claim_ratio: float = 0.0
    """Fraction of numeric/factual assertions in the response that are
    absent from the retrieved context chunks."""

    response_context_overlap: float = 0.0
    """Token-level overlap ratio between response tokens and context tokens."""

    context_utilization: float = 0.0
    """Proportion of context sentences referenced (by token overlap) in the response."""

    safety_heuristic: float = 1.0
    """Separate keyword-rule safety/toxicity check (independent of faithfulness).
    1.0 = safe, 0.0 = detected toxic/unsafe content.
    """

    evaluated: bool = False
    """False when context was missing — all other fields remain at defaults."""

    skip_reason: str = ""
    """Human-readable reason if evaluation was skipped."""


# ---------------------------------------------------------------------------
# Safety keyword patterns (independent of faithfulness)
# ---------------------------------------------------------------------------

_SAFETY_PATTERNS: list[str] = [
    r"\b(kill|murder|harm|abuse|exploit|illegal|weapon|bomb|drugs?)\b",
    r"\b(hate|racist|sexist|discriminat)\b",
    r"\b(suicide|self.?harm)\b",
]
_SAFETY_RE = re.compile("|".join(_SAFETY_PATTERNS), re.IGNORECASE)

# Numeric/factual claim indicators in response text
_FACTUAL_CLAIM_RE = re.compile(
    r"(\b\d[\d,\.%\-]*\b|\b(?:always|never|all|none|every|no one)\b)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tokenizer helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lowercase word-level tokenizer, strips punctuation."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

class LocalHeuristicEvaluator:
    """Evaluate a RAG response against retrieved context chunks.

    Only evaluates spans that carry explicit RAG context.
    Missing context → skip evaluation, all fields remain null.

    Usage::

        evaluator = LocalHeuristicEvaluator()
        result = evaluator.evaluate(
            context_chunks=["Vantage uses DuckDB for telemetry..."],
            response_text="Vantage stores telemetry in DuckDB."
        )
    """

    def evaluate(
        self,
        context_chunks: list[str],
        response_text: str,
    ) -> RAGQualityResult:
        """Run heuristic evaluation. Returns skipped result if inputs are missing."""
        if not context_chunks or not response_text or not response_text.strip():
            return RAGQualityResult(
                evaluated=False,
                skip_reason="Missing context_chunks or response_text — evaluation skipped."
            )

        context_combined = " ".join(context_chunks)
        context_tokens = _tokenize(context_combined)
        response_tokens = _tokenize(response_text)
        context_sentences = _sentence_split(context_combined)
        response_sentences = _sentence_split(response_text)

        if not response_sentences:
            return RAGQualityResult(
                evaluated=False,
                skip_reason="Response produced no parseable sentences."
            )

        # 1. faithfulness_score
        # "supported response claims / total response claims"
        # A response sentence is "supported" if it shares >= 30% token overlap
        # with any single context sentence.
        supported = 0
        for r_sent in response_sentences:
            r_tokens = _tokenize(r_sent)
            if not r_tokens:
                continue
            for c_sent in context_sentences:
                c_tokens = _tokenize(c_sent)
                if not c_tokens:
                    continue
                if len(r_tokens & c_tokens) / len(r_tokens) >= 0.30:
                    supported += 1
                    break
        faithfulness = supported / len(response_sentences)

        # 2. unsupported_claim_ratio
        # Fraction of factual claims in response not found verbatim in context
        factual_claims = _FACTUAL_CLAIM_RE.findall(response_text)
        unsupported_claims = sum(
            1 for c in factual_claims
            if c.lower() not in context_combined.lower()
        )
        unsupported_ratio = (
            unsupported_claims / len(factual_claims) if factual_claims else 0.0
        )

        # 3. response_context_overlap
        # |response_tokens ∩ context_tokens| / |response_tokens|
        overlap_ratio = (
            len(response_tokens & context_tokens) / len(response_tokens)
            if response_tokens else 0.0
        )

        # 4. context_utilization
        # Proportion of context sentences with >= 20% token overlap in the response
        utilized = sum(
            1 for c_sent in context_sentences
            if (c_tok := _tokenize(c_sent))
            and len(c_tok & response_tokens) / len(c_tok) >= 0.20
        )
        utilization = utilized / len(context_sentences) if context_sentences else 0.0

        # 5. safety_heuristic (independent — not mixed into faithfulness)
        safety = 0.0 if _SAFETY_RE.search(response_text) else 1.0

        return RAGQualityResult(
            faithfulness_score=round(faithfulness, 4),
            unsupported_claim_ratio=round(unsupported_ratio, 4),
            response_context_overlap=round(overlap_ratio, 4),
            context_utilization=round(utilization, 4),
            safety_heuristic=safety,
            evaluated=True,
        )
