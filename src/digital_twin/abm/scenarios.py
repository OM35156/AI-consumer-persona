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
    product_category: str = ""
    target_categories: list[str] = field(default_factory=list)
    initial_adopters: dict[str, int] = field(
        default_factory=lambda: {"influencer": 3, "early_adopter": 5}
    )
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

    # 注: YAML の既存キー (target_specialties / therapeutic_area / kol) は下位互換のため
    # そのまま読み込み、内部フィールド（target_categories 等）にマップする。
    # configs/abm_scenarios.yaml のキー改称は別 Issue で扱う。
    for s in cfg.get("scenarios", []):
        yaml_targets = list(s.get("target_categories", s.get("target_specialties", [])))
        events = []
        for e in s.get("events", []):
            events.append(ABMEvent(
                event_type=EventType(e["event_type"]),
                name=e.get("name", ""),
                target_categories=yaml_targets,
                impact_magnitude=e.get("impact_magnitude", 0.1),
                start_step=e.get("start_step", 1),
                duration_steps=e.get("duration_steps", 3),
            ))

        initial = dict(s.get("initial_adopters", {"influencer": 3, "early_adopter": 5}))
        # 旧キー "kol" を "influencer" にマップ（下位互換）
        if "kol" in initial and "influencer" not in initial:
            initial["influencer"] = initial.pop("kol")

        scenarios.append(ABMScenario(
            name=s["name"],
            product=s.get("product", ""),
            product_category=s.get("product_category", s.get("therapeutic_area", "")),
            target_categories=yaml_targets,
            initial_adopters=initial,
            duration_steps=s.get("duration_steps", 24),
            step_unit=s.get("step_unit", "month"),
            events=events,
        ))

    return scenarios


def get_scenario_names(path: str | Path | None = None) -> list[str]:
    """利用可能なシナリオ名一覧を返す."""
    return [s.name for s in load_scenarios(path)]
