"""Data ingestion and loading for physician data."""

import json
from pathlib import Path

from digital_twin.data.schema import Physician, PromotionScenario, SurveyInstrument


def load_physicians(path: str | Path) -> list[Physician]:
    """Load physicians from a JSON file."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Physician.model_validate(r) for r in raw]


def load_surveys(path: str | Path) -> list[SurveyInstrument]:
    """Load survey instruments from a JSON file."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [SurveyInstrument.model_validate(s) for s in raw]


def load_scenarios(path: str | Path) -> list[PromotionScenario]:
    """Load promotion scenarios from a JSON file."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PromotionScenario.model_validate(s) for s in raw]


def load_dataset(
    data_dir: str | Path,
) -> tuple[list[Physician], list[SurveyInstrument], list[PromotionScenario]]:
    """Load a complete dataset from a directory.

    Returns:
        (physicians, surveys, scenarios)
    """
    data_dir = Path(data_dir)
    physicians = load_physicians(data_dir / "physicians.json")
    surveys = load_surveys(data_dir / "surveys.json")

    scenarios_path = data_dir / "scenarios.json"
    scenarios = load_scenarios(scenarios_path) if scenarios_path.exists() else []

    return physicians, surveys, scenarios


def split_holdout(
    physicians: list[Physician],
    holdout_ratio: float = 0.3,
    seed: int = 42,
) -> tuple[list[Physician], list[Physician]]:
    """Split physicians into train and holdout sets."""
    import random

    rng = random.Random(seed)
    shuffled = list(physicians)
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * (1 - holdout_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]
