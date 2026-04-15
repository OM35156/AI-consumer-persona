"""処方シミュレーションモデル — ABM のメインモデル.

設計書 W8 Day4-5 に対応。エージェント集団、ネットワーク、
タイムステップを管理する。configs/base.yaml の abm セクションから設定を読み込む。
"""

from __future__ import annotations

import logging

import mesa
from omegaconf import DictConfig

from digital_twin.abm.consumer_agent import (
    DEFAULT_CONSIDERING_FACTOR,
    DEFAULT_INFLUENCER_THRESHOLD,
    AdoptionState,
    AgentProfile,
    ConsumerAgent,
)
from digital_twin.abm.network import build_consumer_network

logger = logging.getLogger(__name__)


def _load_abm_config() -> DictConfig | None:
    """ABM 設定を読み込む（失敗時は None）."""
    try:
        from digital_twin.utils.config import load_config
        config = load_config()
        return config.get("abm")
    except Exception:
        return None


class PrescriptionModel(mesa.Model):
    """処方行動の社会シミュレーションモデル."""

    def __init__(
        self,
        agent_profiles: list[AgentProfile],
        seed: int = 42,
        kol_influence: float | None = None,
        peer_influence: float | None = None,
        config: DictConfig | None = None,
    ) -> None:
        super().__init__(seed=seed)

        # config 読込（明示的に渡されなければファイルから読む）
        cfg = config or _load_abm_config()

        self.kol_influence = kol_influence or (cfg.influence.kol_influence if cfg else 0.15)
        self.peer_influence = peer_influence or (cfg.influence.peer_influence if cfg else 0.05)
        self.step_unit = cfg.step_unit if cfg else "month"
        self.step_label = cfg.step_label if cfg else "ヶ月"
        self._steps = 0

        # agent config
        # 注: config キー名 kol_threshold は下位互換のため維持（#4 で configs/ 整理時に改称予定）
        influencer_threshold = cfg.agent.kol_threshold if cfg else DEFAULT_INFLUENCER_THRESHOLD
        considering_factor = cfg.agent.considering_factor if cfg else DEFAULT_CONSIDERING_FACTOR

        # network config
        net_seed = cfg.network.seed if cfg else seed
        net_params = {}
        if cfg and cfg.get("network"):
            # 注: config キー名（same_specialty_prob 等）は下位互換のため維持。
            # configs/base.yaml 側の改称は別 Issue で対応する。
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
                considering_factor=considering_factor,
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
            if agent.state != AdoptionState.ADOPTED:
                continue

            neighbors = list(self.network.neighbors(agent.unique_id))
            for neighbor_id in neighbors:
                neighbor = self._get_agent_by_id(neighbor_id)
                if neighbor and neighbor.state != AdoptionState.ADOPTED:
                    influence = self.kol_influence if agent.is_influencer else self.peer_influence
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
        """採用状態ごとのエージェント数."""
        counts = {s.value: 0 for s in AdoptionState}
        for agent in self._agents_list:
            counts[agent.state.value] += 1
        return counts

    def get_adoption_rate(self) -> float:
        """採用率."""
        total = len(self._agents_list)
        if total == 0:
            return 0.0
        adopted = sum(1 for a in self._agents_list if a.state == AdoptionState.ADOPTED)
        return adopted / total

    def run(self, steps: int = 50) -> list[dict]:
        """複数ステップを実行し、各ステップの状態を返す."""
        history = []
        for _ in range(steps):
            self.step()
            history.append({
                "step": self._steps,
                **self.get_adoption_count(),
                "adoption_rate": self.get_adoption_rate(),
            })
        return history
