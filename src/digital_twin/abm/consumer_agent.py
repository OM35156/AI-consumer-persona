"""生活者エージェント — ABM のエージェント定義.

医師版 ABM から派生。セグメントプロファイルから属性を設定し、
採用閾値に基づいて購買・採用行動を決定する。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import mesa

# デフォルト値（config で上書き可能）
DEFAULT_INFLUENCER_THRESHOLD = 0.7
DEFAULT_CONSIDERING_FACTOR = 0.5


class AdoptionState(StrEnum):
    """採用状態（認知→検討→採用）."""

    NOT_ADOPTED = "not_adopted"
    CONSIDERING = "considering"
    ADOPTED = "adopted"


@dataclass
class AgentProfile:
    """エージェントのプロファイル（セグメントプロファイルから設定）."""

    category: str = ""                # 関心カテゴリ（スキンケア/サプリ/ガジェット等）
    income_bracket: str = ""          # 世帯年収層
    age_range: str = ""               # 年代層
    influencer_score: float = 0.0     # 影響力スコア（インフルエンサー傾向）
    receptivity: float = 0.5          # 新商品受容性（0-1）
    adoption_threshold: float = 0.5   # 採用閾値（0-1）
    current_brand_share: float = 0.0  # 現在の対象ブランド利用シェア


class ConsumerAgent(mesa.Agent):
    """生活者エージェント."""

    def __init__(
        self,
        model: mesa.Model,
        profile: AgentProfile | None = None,
        influencer_threshold: float = DEFAULT_INFLUENCER_THRESHOLD,
        considering_factor: float = DEFAULT_CONSIDERING_FACTOR,
    ) -> None:
        super().__init__(model)
        self.profile = profile or AgentProfile()
        self.state = AdoptionState.NOT_ADOPTED
        self.influence_accumulated = 0.0
        self.adoption_step: int | None = None
        self._influencer_threshold = influencer_threshold
        self._considering_factor = considering_factor

    @property
    def is_influencer(self) -> bool:
        """インフルエンサー（高影響力）かどうか."""
        return self.profile.influencer_score >= self._influencer_threshold

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
