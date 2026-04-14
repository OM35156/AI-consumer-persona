"""ABM シナリオ定義 — プリセットおよびカスタムシナリオの管理.

configs/abm_scenarios.yaml からシナリオを読み込む。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from omegaconf import OmegaConf

from digital_twin.abm.events import ABMEvent, EventType

logger = logging.getLogger(__name__)

_SCENARIOS_PATH = Path(__file__).resolve().parents[3] / "configs" / "abm_scenarios.yaml"


@dataclass
class ABMScenario:
    """ABM シミュレーションシナリオ."""

    name: str = ""
    product: str = ""
    therapeutic_area: str = ""
    target_specialties: list[str] = field(default_factory=list)
    initial_adopters: dict[str, int] = field(default_factory=lambda: {"kol": 3, "early_adopter": 5})
    duration_steps: int = 24
    step_unit: str = "month"
    events: list[ABMEvent] = field(default_factory=list)


def load_scenarios(path: str | Path | None = None) -> list[ABMScenario]:
    """YAML ファイルからシナリオを読み込む."""
    path = Path(path) if path else _SCENARIOS_PATH
    if not path.exists():
        logger.warning(f"シナリオファイルが見つかりません: {path}")
        return []

    cfg = OmegaConf.load(path)
    scenarios: list[ABMScenario] = []

    for s in cfg.get("scenarios", []):
        events = []
        for e in s.get("events", []):
            events.append(ABMEvent(
                event_type=EventType(e["event_type"]),
                name=e.get("name", ""),
                target_specialties=list(s.get("target_specialties", [])),
                impact_magnitude=e.get("impact_magnitude", 0.1),
                start_step=e.get("start_step", 1),
                duration_steps=e.get("duration_steps", 3),
            ))

        scenarios.append(ABMScenario(
            name=s["name"],
            product=s.get("product", ""),
            therapeutic_area=s.get("therapeutic_area", ""),
            target_specialties=list(s.get("target_specialties", [])),
            initial_adopters=dict(s.get("initial_adopters", {"kol": 3, "early_adopter": 5})),
            duration_steps=s.get("duration_steps", 24),
            step_unit=s.get("step_unit", "month"),
            events=events,
        ))

    return scenarios


def get_scenario_names(path: str | Path | None = None) -> list[str]:
    """利用可能なシナリオ名一覧を返す."""
    return [s.name for s in load_scenarios(path)]
