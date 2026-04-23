"""データブリッジ — 実データから ABM エージェントプロファイルへの変換.

Consumer スキーマおよび SegmentProfile から AgentProfile を生成する。
"""

from __future__ import annotations

import random

from digital_twin.abm.consumer_agent import AgentProfile
from digital_twin.data.schema import Consumer
from digital_twin.data.segment_profile import SegmentProfile

# 新商品受容性 → 段階別閾値のマッピング
_RECEPTIVITY_MAP = {
    "early": {
        "receptivity": 0.8,
        "aware_threshold": 0.05,
        "interest_threshold": 0.15,
        "purchase_threshold": 0.25,
        "repeat_threshold": 0.4,
    },
    "moderate": {
        "receptivity": 0.5,
        "aware_threshold": 0.1,
        "interest_threshold": 0.3,
        "purchase_threshold": 0.55,
        "repeat_threshold": 0.75,
    },
    "late": {
        "receptivity": 0.2,
        "aware_threshold": 0.15,
        "interest_threshold": 0.45,
        "purchase_threshold": 0.8,
        "repeat_threshold": 0.95,
    },
}

# 年代グループ → 年代ラベル（生活者版の AgeGroup enum に対応）
_AGE_TO_NENDAI = {
    "18-24": "10代後半〜20代前半",
    "25-34": "20代後半〜30代前半",
    "35-44": "30代後半〜40代前半",
    "45-54": "40代後半〜50代前半",
    "55-64": "50代後半〜60代前半",
    "65+": "65歳以上",
}


def consumer_to_agent_profile(consumer: Consumer) -> AgentProfile:
    """個別の Consumer データから AgentProfile を生成する."""
    demo = consumer.demographics
    cat = consumer.category_profile

    recv = cat.new_product_receptivity
    recv_params = _RECEPTIVITY_MAP.get(recv, _RECEPTIVITY_MAP["moderate"])

    return AgentProfile(
        category=cat.category,
        income_bracket=demo.household_income or "未設定",
        age_range=_AGE_TO_NENDAI.get(demo.age_group.value, demo.age_group.value),
        gender=demo.gender.value,
        influencer_score=0.9 if demo.is_influencer else 0.3,
        receptivity=recv_params["receptivity"],
        aware_threshold=recv_params["aware_threshold"],
        interest_threshold=recv_params["interest_threshold"],
        purchase_threshold=recv_params["purchase_threshold"],
        repeat_threshold=recv_params["repeat_threshold"],
        current_brand_share=0.0,
    )


def consumers_to_agent_profiles(consumers: list[Consumer]) -> list[AgentProfile]:
    """複数の Consumer から AgentProfile リストを生成する."""
    return [consumer_to_agent_profile(c) for c in consumers]


def segment_profile_to_agents(
    profile: SegmentProfile,
    n: int = 30,
    seed: int = 42,
) -> list[AgentProfile]:
    """セグメントプロファイルから N 体のエージェントを分布に従い生成する.

    注: SegmentProfile は現状医師版スキーマのまま（specialty/bed_size/
    new_drug_receptivity/mr_contact を含む）。本関数は過渡期のブリッジとして、
    SegmentProfile の各フィールドを AgentProfile の汎用スロット
    （category/income_bracket）にマップする。SegmentProfile の生活者版化は
    別 Issue で扱う。
    """
    rng = random.Random(seed)
    agents: list[AgentProfile] = []

    ndr = profile.new_drug_receptivity

    # 受容性分布からカテゴリ別人数を算出
    categories = [
        ("early", ndr.early_prescriber, 0.8, 0.05, 0.15, 0.25, 0.4),
        ("relatively_early", ndr.relatively_early, 0.65, 0.07, 0.2, 0.35, 0.55),
        ("wait_and_see", ndr.wait_and_see, 0.5, 0.1, 0.3, 0.55, 0.75),
        ("majority", ndr.majority_prescribes, 0.35, 0.12, 0.38, 0.7, 0.85),
        ("after_established", ndr.after_established, 0.2, 0.15, 0.45, 0.8, 0.95),
    ]

    # インフルエンサー比率の推定
    max_contact_rate = max(profile.mr_contact.values()) if profile.mr_contact else 0.3
    influencer_ratio = min(0.15, max_contact_rate * 0.1)

    for _i in range(n):
        weights = [c[1] for c in categories]
        total = sum(weights)
        if total == 0:
            weights = [0.2] * 5
            total = 1.0
        weights = [w / total for w in weights]

        cat_idx = rng.choices(range(len(categories)), weights=weights, k=1)[0]
        _, _, receptivity, aware_th, interest_th, purchase_th, repeat_th = categories[cat_idx]

        # ばらつきを追加
        receptivity += rng.gauss(0, 0.05)
        aware_th += rng.gauss(0, 0.02)
        interest_th += rng.gauss(0, 0.03)
        purchase_th += rng.gauss(0, 0.05)
        repeat_th += rng.gauss(0, 0.05)

        receptivity = max(0.05, min(0.95, receptivity))
        aware_th = max(0.01, min(0.5, aware_th))
        interest_th = max(aware_th + 0.01, min(0.7, interest_th))
        purchase_th = max(interest_th + 0.01, min(0.9, purchase_th))
        repeat_th = max(purchase_th + 0.01, min(0.99, repeat_th))

        is_high_influence = rng.random() < influencer_ratio

        agents.append(AgentProfile(
            category=profile.specialty,
            income_bracket=profile.bed_size,
            age_range=profile.age_range,
            influencer_score=0.9 if is_high_influence else rng.uniform(0.1, 0.5),
            receptivity=round(receptivity, 3),
            aware_threshold=round(aware_th, 3),
            interest_threshold=round(interest_th, 3),
            purchase_threshold=round(purchase_th, 3),
            repeat_threshold=round(repeat_th, 3),
        ))

    return agents
