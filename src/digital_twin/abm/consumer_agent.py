"""生活者エージェント — ABM のエージェント定義.

生活者の商品浸透ファネル（未認知→認知→関心→購買→リピート）を
シミュレーションするためのエージェント。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import mesa

# デフォルト値（config で上書き可能）
DEFAULT_INFLUENCER_THRESHOLD = 0.7


class AdoptionState(StrEnum):
    """採用状態（5段階ファネル）."""

    UNAWARE = "unaware"          # 未認知
    AWARE = "aware"              # 認知
    INTERESTED = "interested"    # 関心
    PURCHASED = "purchased"      # 購買
    REPEAT = "repeat"            # リピート


# 状態の順序（遷移判定用）
_STATE_ORDER = list(AdoptionState)


@dataclass
class AgentProfile:
    """エージェントのプロファイル（セグメントプロファイルから設定）."""

    category: str = ""                # 関心カテゴリ（スキンケア/サプリ/ガジェット等）
    income_bracket: str = ""          # 世帯年収層
    age_range: str = ""               # 年代層
    gender: str = ""                  # 性別
    influencer_score: float = 0.0     # 影響力スコア（インフルエンサー傾向）
    receptivity: float = 0.5          # 新商品受容性（0-1）
    # 段階別閾値: influence_accumulated がこの値を超えると次の状態へ遷移
    aware_threshold: float = 0.1      # 未認知→認知
    interest_threshold: float = 0.3   # 認知→関心
    purchase_threshold: float = 0.6   # 関心→購買
    repeat_threshold: float = 0.8     # 購買→リピート
    current_brand_share: float = 0.0  # 現在の対象ブランド利用シェア

    @property
    def thresholds(self) -> dict[AdoptionState, float]:
        """各状態への遷移閾値を返す."""
        return {
            AdoptionState.AWARE: self.aware_threshold,
            AdoptionState.INTERESTED: self.interest_threshold,
            AdoptionState.PURCHASED: self.purchase_threshold,
            AdoptionState.REPEAT: self.repeat_threshold,
        }


class ConsumerAgent(mesa.Agent):
    """生活者エージェント."""

    def __init__(
        self,
        model: mesa.Model,
        profile: AgentProfile | None = None,
        influencer_threshold: float = DEFAULT_INFLUENCER_THRESHOLD,
    ) -> None:
        super().__init__(model)
        self.profile = profile or AgentProfile()
        self.state = AdoptionState.UNAWARE
        self.influence_accumulated = 0.0
        self.adoption_step: int | None = None
        self._influencer_threshold = influencer_threshold

    @property
    def is_influencer(self) -> bool:
        """インフルエンサー（高影響力）かどうか."""
        return self.profile.influencer_score >= self._influencer_threshold

    def receive_influence(self, amount: float) -> None:
        """他のエージェントから影響を受ける."""
        self.influence_accumulated += amount

    def step(self) -> None:
        """1ステップの行動: 閾値を超えていれば状態を遷移させる."""
        if self.state == AdoptionState.REPEAT:
            return  # 最終状態

        current_idx = _STATE_ORDER.index(self.state)
        next_state = _STATE_ORDER[current_idx + 1]
        threshold = self.profile.thresholds[next_state]

        if self.influence_accumulated >= threshold:
            self.state = next_state
            if next_state == AdoptionState.PURCHASED:
                self.adoption_step = self.model._steps if hasattr(self.model, "_steps") else 0
