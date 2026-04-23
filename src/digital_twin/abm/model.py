"""社会シミュレーションモデル — ABM のメインモデル.

生活者エージェント集団のネットワーク上で商品浸透ファネル
（未認知→認知→関心→購買→リピート）をシミュレーションする。
"""

from __future__ import annotations

import logging

import mesa
from omegaconf import DictConfig

from digital_twin.abm.consumer_agent import (
    DEFAULT_INFLUENCER_THRESHOLD,
    AdoptionState,
    AgentProfile,
    ConsumerAgent,
)
from digital_twin.abm.network import build_consumer_network

logger = logging.getLogger(__name__)

# 購買以上の状態（周囲に影響を与える状態）
_INFLUENCING_STATES = {AdoptionState.PURCHASED, AdoptionState.REPEAT}

# リピーターの口コミ強化係数
DEFAULT_REPEAT_MULTIPLIER = 1.5


def _load_abm_config() -> DictConfig | None:
    """ABM 設定を読み込む（失敗時は None）."""
    try:
        from digital_twin.utils.config import load_config
        config = load_config()
        return config.get("abm")
    except Exception:
        return None


class PrescriptionModel(mesa.Model):
    """商品浸透の社会シミュレーションモデル."""

    def __init__(
        self,
        agent_profiles: list[AgentProfile],
        seed: int = 42,
        kol_influence: float | None = None,
        peer_influence: float | None = None,
        repeat_multiplier: float | None = None,
        config: DictConfig | None = None,
    ) -> None:
        super().__init__(seed=seed)

        # config 読込（明示的に渡されなければファイルから読む）
        cfg = config or _load_abm_config()

        self.kol_influence = kol_influence or (cfg.influence.kol_influence if cfg else 0.15)
        self.peer_influence = peer_influence or (cfg.influence.peer_influence if cfg else 0.05)
        self.repeat_multiplier = repeat_multiplier or (
            cfg.influence.repeat_multiplier if cfg and cfg.influence.get("repeat_multiplier") else DEFAULT_REPEAT_MULTIPLIER
        )
        self.step_unit = cfg.step_unit if cfg else "month"
        self.step_label = cfg.step_label if cfg else "ヶ月"
        self._steps = 0

        # agent config
        influencer_threshold = cfg.agent.kol_threshold if cfg else DEFAULT_INFLUENCER_THRESHOLD

        # network config
        net_seed = cfg.network.seed if cfg else seed
        net_params = {}
        if cfg and cfg.get("network"):
            net_params = {
                "same_category_prob": cfg.network.same_specialty_prob,
                "same_income_prob": cfg.network.same_bed_size_prob,
                "influencer_connection_prob": cfg.network.kol_connection_prob,
            }

        # エージェント作成
        self._agents_list: list[ConsumerAgent] = []
        for profile in agent_profiles:
            agent = ConsumerAgent(
                self,
                profile=profile,
                influencer_threshold=influencer_threshold,
            )
            self._agents_list.append(agent)

        # ネットワーク構築
        self.network = build_consumer_network(self._agents_list, seed=net_seed, **net_params)

    @property
    def consumer_agents(self) -> list[ConsumerAgent]:
        """生活者エージェント一覧."""
        return self._agents_list

    def step(self) -> None:
        """1タイムステップを実行する."""
        self._steps += 1

        for agent in self._agents_list:
            if agent.state not in _INFLUENCING_STATES:
                continue

            # リピーターは口コミ影響力が強化される
            multiplier = self.repeat_multiplier if agent.state == AdoptionState.REPEAT else 1.0
            base_influence = self.kol_influence if agent.is_influencer else self.peer_influence
            influence = base_influence * multiplier

            neighbors = list(self.network.neighbors(agent.unique_id))
            for neighbor_id in neighbors:
                neighbor = self._get_agent_by_id(neighbor_id)
                if neighbor and neighbor.state != AdoptionState.REPEAT:
                    neighbor.receive_influence(influence)

        for agent in self._agents_list:
            agent.step()

    def _get_agent_by_id(self, agent_id: int) -> ConsumerAgent | None:
        """ID からエージェントを取得する."""
        for agent in self._agents_list:
            if agent.unique_id == agent_id:
                return agent
        return None

    def get_adoption_count(self) -> dict[str, int]:
        """ファネル段階ごとのエージェント数."""
        counts = {s.value: 0 for s in AdoptionState}
        for agent in self._agents_list:
            counts[agent.state.value] += 1
        return counts

    def get_purchase_rate(self) -> float:
        """購買到達率（購買+リピート）."""
        total = len(self._agents_list)
        if total == 0:
            return 0.0
        purchased = sum(
            1 for a in self._agents_list
            if a.state in {AdoptionState.PURCHASED, AdoptionState.REPEAT}
        )
        return purchased / total

    def run(self, steps: int = 50) -> list[dict]:
        """複数ステップを実行し、各ステップの状態を返す."""
        history = []
        for _ in range(steps):
            self.step()
            history.append({
                "step": self._steps,
                **self.get_adoption_count(),
                "purchase_rate": self.get_purchase_rate(),
            })
        return history
