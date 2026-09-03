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

    def __init__(self, prices_path: Path | str | None = None):
        self._prices: dict[str, dict] = {}
        target_path = Path(prices_path) if prices_path else Path("vantage/data/model_prices.json")
        self._load(target_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("model_prices_not_found", path=str(path))
            return
        try:
            raw = json.loads(path.read_text())
            self._prices = {k: v for k, v in raw.items() if not k.startswith("_")}
            logger.info("pricing_loaded", count=len(self._prices), path=str(path))
        except Exception:
            pass

    def calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        cost = self.compute(model_name, prompt_tokens, completion_tokens)
        if cost is not None:
            return round(cost, 6)
        # Default fallback pricing for standard models (e.g. gpt-4o rates: $2.50 / 1M in, $10.00 / 1M out)
        in_rate = 0.0000025
        out_rate = 0.000010
        return round((prompt_tokens * in_rate) + (completion_tokens * out_rate), 6)

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
