"""情報伝播モデル — 独立カスケードおよび線形閾値モデル.

設計書 W9 Day1-2 に対応。KOL スコア、受容閾値、情報減衰率をパラメータとする。
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from digital_twin.abm.consumer_agent import AdoptionState, ConsumerAgent


class PropagationModel(ABC):
    """情報伝播モデルの共通インターフェース."""

    @abstractmethod
    def propagate(
        self,
        agents: list[ConsumerAgent],
        network: dict[int, list[int]],
    ) -> int:
        """1ステップの伝播を実行し、新規採用数を返す."""

    def get_adoption_count(self, agents: list[ConsumerAgent]) -> int:
        """採用済みエージェント数."""
        return sum(1 for a in agents if a.state == AdoptionState.ADOPTED)


class IndependentCascadeModel(PropagationModel):
    """独立カスケードモデル — エッジごとの確率ベース伝播."""

    def __init__(
        self,
        base_probability: float = 0.05,
        kol_boost: float = 0.15,
        decay_rate: float = 0.95,
        seed: int = 42,
    ) -> None:
        self.base_probability = base_probability
        self.kol_boost = kol_boost
        self.decay_rate = decay_rate
        self._rng = random.Random(seed)
        self._step_count = 0

    def propagate(
        self,
        agents: list[ConsumerAgent],
        network: dict[int, list[int]],
    ) -> int:
        self._step_count += 1
        decay_factor = self.decay_rate ** self._step_count
        new_adopters = 0

        agent_map = {a.unique_id: a for a in agents}

        # 新規採用済みエージェントからのみ伝播（活性化したステップのみ）
        for agent in agents:
            if agent.state != AdoptionState.ADOPTED:
                continue

            neighbors = network.get(agent.unique_id, [])
            for neighbor_id in neighbors:
                neighbor = agent_map.get(neighbor_id)
                if not neighbor or neighbor.state == AdoptionState.ADOPTED:
                    continue

                prob = self.base_probability * decay_factor
                if agent.is_influencer:
                    prob += self.kol_boost

                if self._rng.random() < prob:
                    neighbor.receive_influence(prob)

        # 閾値判定
        for agent in agents:
            if agent.state != AdoptionState.ADOPTED:
                prev_state = agent.state
                agent.step()
                if agent.state == AdoptionState.ADOPTED and prev_state != AdoptionState.ADOPTED:
                    new_adopters += 1

        return new_adopters


class LinearThresholdModel(PropagationModel):
    """線形閾値モデル — 隣接エージェントの累積影響 vs 閾値."""

    def __init__(
        self,
        kol_weight: float = 0.15,
        peer_weight: float = 0.05,
        decay_rate: float = 0.95,
    ) -> None:
        self.kol_weight = kol_weight
        self.peer_weight = peer_weight
        self.decay_rate = decay_rate
        self._step_count = 0

    def propagate(
        self,
        agents: list[ConsumerAgent],
        network: dict[int, list[int]],
    ) -> int:
        self._step_count += 1
        decay_factor = self.decay_rate ** self._step_count
        new_adopters = 0

        agent_map = {a.unique_id: a for a in agents}

        for agent in agents:
            if agent.state == AdoptionState.ADOPTED:
                continue

            neighbors = network.get(agent.unique_id, [])
            total_influence = 0.0

            for neighbor_id in neighbors:
                neighbor = agent_map.get(neighbor_id)
                if not neighbor or neighbor.state != AdoptionState.ADOPTED:
                    continue

                weight = self.kol_weight if neighbor.is_influencer else self.peer_weight
                total_influence += weight * decay_factor

            if total_influence > 0:
                agent.receive_influence(total_influence)

        # 閾値判定
        for agent in agents:
            if agent.state != AdoptionState.ADOPTED:
                prev_state = agent.state
                agent.step()
                if agent.state == AdoptionState.ADOPTED and prev_state != AdoptionState.ADOPTED:
                    new_adopters += 1

        return new_adopters
