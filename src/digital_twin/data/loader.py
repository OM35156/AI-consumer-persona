"""生活者データの読み込み."""

import json
import random
from pathlib import Path

from digital_twin.data.schema import Consumer, PromotionScenario, SurveyInstrument


def load_consumers(path: str | Path) -> list[Consumer]:
    """JSON ファイルから Consumer リストを読み込む."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Consumer.model_validate(r) for r in raw]


def load_surveys(path: str | Path) -> list[SurveyInstrument]:
    """JSON ファイルから調査票リストを読み込む."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [SurveyInstrument.model_validate(s) for s in raw]


def load_scenarios(path: str | Path) -> list[PromotionScenario]:
    """JSON ファイルからプロモーションシナリオリストを読み込む."""
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [PromotionScenario.model_validate(s) for s in raw]


def load_dataset(
    data_dir: str | Path,
) -> tuple[list[Consumer], list[SurveyInstrument], list[PromotionScenario]]:
    """ディレクトリから完全なデータセットを読み込む.

    期待するファイル:
        consumers.json (必須)、surveys.json (必須)、scenarios.json (任意)

    Returns:
        (consumers, surveys, scenarios)
    """
    data_dir = Path(data_dir)
    consumers = load_consumers(data_dir / "consumers.json")
    surveys_path = data_dir / "surveys.json"
    surveys = load_surveys(surveys_path) if surveys_path.exists() else []

    scenarios_path = data_dir / "scenarios.json"
    scenarios = load_scenarios(scenarios_path) if scenarios_path.exists() else []

    return consumers, surveys, scenarios


def split_holdout(
    consumers: list[Consumer],
    holdout_ratio: float = 0.3,
    seed: int = 42,
) -> tuple[list[Consumer], list[Consumer]]:
    """生活者を train と holdout に分割する."""
    rng = random.Random(seed)
    shuffled = list(consumers)
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * (1 - holdout_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]
