import json
from pathlib import Path
from vantage.domain.events import TelemetryEnvelope, LLMCallData
from vantage.core.logging import get_logger

logger = get_logger(__name__)


class CostEnricher:
    """
    Single source of truth for LLM token pricing.
    Loads from model_prices.json once at application startup.
    """

    def __init__(self, prices_path: Path):
        self._prices: dict[str, dict] = {}
        self._load(prices_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("model_prices_not_found", path=str(path))
            return
        raw = json.loads(path.read_text())
        # Filter out metadata top-level key if present
        self._prices = {k: v for k, v in raw.items() if not k.startswith("_")}
        logger.info("pricing_loaded", count=len(self._prices), path=str(path))

    def compute(self, model: str, tokens_in: int | None, tokens_out: int | None) -> float | None:
        if not model or tokens_in is None or tokens_out is None:
            return None
        entry = self._prices.get(model)
        if not entry:
            logger.warning("model_price_unknown", model=model)
            return None
        return (
            tokens_in * entry["input_per_token"]
            + tokens_out * entry["output_per_token"]
        )

    async def apply(self, envelope: TelemetryEnvelope) -> TelemetryEnvelope:
        payload = envelope.payload
        if isinstance(payload, LLMCallData) and payload.cost_usd is None:
            cost = self.compute(payload.model_name, payload.tokens_input, payload.tokens_output)
            if cost is not None:
                payload = payload.model_copy(update={"cost_usd": cost})
                return envelope.model_copy(update={"payload": payload})
        return envelope
