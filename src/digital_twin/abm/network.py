"""医師ネットワーク — ABM のネットワークトポロジー定義.

同一施設・同一地域・学会接点の3種のエッジで構成。
"""

from __future__ import annotations

import random

import networkx as nx

from digital_twin.abm.physician_agent import PhysicianAgent


def build_physician_network(
    agents: list[PhysicianAgent],
    same_specialty_prob: float = 0.3,
    same_bed_size_prob: float = 0.15,
    kol_connection_prob: float = 0.5,
    seed: int = 42,
) -> nx.Graph:
    """エージェント間のネットワークを構築する.

    Args:
        agents: 医師エージェントのリスト
        same_specialty_prob: 同一診療科でのエッジ確率
        same_bed_size_prob: 同一病床数区分でのエッジ確率
        kol_connection_prob: KOL とのエッジ確率（追加）
        seed: 乱数シード
    """
    rng = random.Random(seed)
    g = nx.Graph()

    for agent in agents:
        g.add_node(agent.unique_id, agent=agent)

    for i, a1 in enumerate(agents):
        for a2 in agents[i + 1 :]:
            p = 0.0

            # 同一診療科
            if a1.profile.specialty == a2.profile.specialty:
                p += same_specialty_prob

            # 同一病床数区分
            if a1.profile.bed_size == a2.profile.bed_size:
                p += same_bed_size_prob

            # KOL 接続（学会接点）
            if a1.is_kol or a2.is_kol:
                p += kol_connection_prob

            if rng.random() < min(p, 1.0):
                g.add_edge(a1.unique_id, a2.unique_id)

    return g
