"""医師エージェント — ABM のエージェント定義.

設計書 W8 Day4-5 に対応。セグメントプロファイルから属性を設定し、
採用閾値に基づいて処方行動を決定する。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import mesa

# デフォルト値（config で上書き可能）
DEFAULT_KOL_THRESHOLD = 0.7
DEFAULT_CONSIDERING_FACTOR = 0.5


class AdoptionState(StrEnum):
    """薬剤採用状態."""

    NOT_ADOPTED = "not_adopted"
    CONSIDERING = "considering"
    ADOPTED = "adopted"


@dataclass
class AgentProfile:
    """エージェントのプロファイル（セグメントプロファイルから設定）."""

    specialty: str = ""
    bed_size: str = ""
    age_range: str = ""
    kol_score: float = 0.0
    receptivity: float = 0.5
    adoption_threshold: float = 0.5
    current_rx_share: float = 0.0


class PhysicianAgent(mesa.Agent):
    """医師エージェント."""

    def __init__(
        self,
        model: mesa.Model,
        profile: AgentProfile | None = None,
        kol_threshold: float = DEFAULT_KOL_THRESHOLD,
        considering_factor: float = DEFAULT_CONSIDERING_FACTOR,
    ) -> None:
        super().__init__(model)
        self.profile = profile or AgentProfile()
        self.state = AdoptionState.NOT_ADOPTED
        self.influence_accumulated = 0.0
        self.adoption_step: int | None = None
        self._kol_threshold = kol_threshold
        self._considering_factor = considering_factor

    @property
    def is_kol(self) -> bool:
        """KOL かどうか."""
        return self.profile.kol_score >= self._kol_threshold

    def receive_influence(self, amount: float) -> None:
        """他のエージェントから影響を受ける."""
        self.influence_accumulated += amount
        if (
            self.state == AdoptionState.NOT_ADOPTED
            and self.influence_accumulated > self.profile.adoption_threshold * self._considering_factor
        ):
            self.state = AdoptionState.CONSIDERING

    def step(self) -> None:
        """1ステップの行動."""
        if self.state == AdoptionState.ADOPTED:
            return

        if self.influence_accumulated >= self.profile.adoption_threshold:
            self.state = AdoptionState.ADOPTED
            self.adoption_step = self.model._steps if hasattr(self.model, "_steps") else 0
