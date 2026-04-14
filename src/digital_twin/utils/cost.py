"""LLM API cost tracking utility."""

from dataclasses import dataclass, field
from datetime import datetime


# Approximate pricing per 1M tokens (USD) as of 2025
_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}


@dataclass
class APICallRecord:
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def cost_usd(self) -> float:
        pricing = _PRICING.get(self.model, {"input": 10.0, "output": 50.0})
        return (
            self.input_tokens * pricing["input"] / 1_000_000
            + self.output_tokens * pricing["output"] / 1_000_000
        )


class CostTracker:
    """Tracks cumulative API costs across a session."""

    def __init__(self) -> None:
        self.records: list[APICallRecord] = []

    def record(self, model: str, input_tokens: int, output_tokens: int) -> APICallRecord:
        entry = APICallRecord(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        self.records.append(entry)
        return entry

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self.records)

    @property
    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self.records)

    def summary(self) -> dict:
        return {
            "total_calls": len(self.records),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
        }
