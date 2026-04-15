"""生活者ネットワーク — ABM のネットワークトポロジー定義.

同一カテゴリ関心・同一世帯年収層・インフルエンサー接点の3種のエッジで構成。
"""

from __future__ import annotations

import random

import networkx as nx

from digital_twin.abm.consumer_agent import ConsumerAgent


def build_consumer_network(
    agents: list[ConsumerAgent],
    same_category_prob: float = 0.3,
    same_income_prob: float = 0.15,
    influencer_connection_prob: float = 0.5,
    seed: int = 42,
) -> nx.Graph:
    """エージェント間のネットワークを構築する.

    Args:
        agents: 生活者エージェントのリスト
        same_category_prob: 同一関心カテゴリでのエッジ確率
        same_income_prob: 同一世帯年収層でのエッジ確率
        influencer_connection_prob: インフルエンサーとのエッジ確率（追加）
        seed: 乱数シード
    """
    rng = random.Random(seed)
    g = nx.Graph()

    for agent in agents:
        g.add_node(agent.unique_id, agent=agent)

    for i, a1 in enumerate(agents):
        for a2 in agents[i + 1 :]:
            p = 0.0

            # 同一関心カテゴリ
            if a1.profile.category == a2.profile.category:
                p += same_category_prob

            # 同一世帯年収層
            if a1.profile.income_bracket == a2.profile.income_bracket:
                p += same_income_prob

            # インフルエンサー接続（SNS 波及・口コミ発信源）
            if a1.is_influencer or a2.is_influencer:
                p += influencer_connection_prob

            if rng.random() < min(p, 1.0):
                g.add_edge(a1.unique_id, a2.unique_id)

    return g
