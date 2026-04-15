"""データブリッジ — 実データから ABM エージェントプロファイルへの変換.

Physician スキーマおよび SegmentProfile から AgentProfile を生成する。
"""

from __future__ import annotations

import random

from digital_twin.abm.consumer_agent import AgentProfile
from digital_twin.data.schema import Physician
from digital_twin.data.segment_profile import SegmentProfile

# 新薬採用速度 → 受容性スコア / 採用閾値のマッピング
_ADOPTION_SPEED_MAP = {
    "early": {"receptivity": 0.8, "adoption_threshold": 0.2},
    "moderate": {"receptivity": 0.5, "adoption_threshold": 0.5},
    "late": {"receptivity": 0.2, "adoption_threshold": 0.8},
}

# 施設タイプ → 病床数区分のマッピング
_FACILITY_TO_BEDSIZE = {
    "university_hospital": "500床以上",
    "cancer_center": "500床以上",
    "general_hospital": "200-499床",
    "specialized_hospital": "200-499床",
    "clinic": "20床未満",
}

# 年齢グループ → 年代のマッピング
_AGE_TO_NENDAI = {
    "30-39": "30代",
    "40-49": "40代",
    "50-59": "50代",
    "60-69": "60代",
    "70+": "70代以上",
}


def physician_to_agent_profile(physician: Physician) -> AgentProfile:
    """個別の Physician データから AgentProfile を生成する."""
    demo = physician.demographics
    rx = physician.prescription_profile

    speed = rx.new_drug_adoption_speed
    speed_params = _ADOPTION_SPEED_MAP.get(speed, _ADOPTION_SPEED_MAP["moderate"])

    return AgentProfile(
        specialty=demo.specialty.value,
        bed_size=_FACILITY_TO_BEDSIZE.get(demo.facility_type.value, "200-499床"),
        age_range=_AGE_TO_NENDAI.get(demo.age_group.value, "50代"),
        kol_score=0.9 if demo.is_key_opinion_leader else 0.3,
        receptivity=speed_params["receptivity"],
        adoption_threshold=speed_params["adoption_threshold"],
        current_rx_share=0.0,
    )


def physicians_to_agent_profiles(physicians: list[Physician]) -> list[AgentProfile]:
    """複数の Physician から AgentProfile リストを生成する."""
    return [physician_to_agent_profile(p) for p in physicians]


def segment_profile_to_agents(
    profile: SegmentProfile,
    n: int = 30,
    seed: int = 42,
) -> list[AgentProfile]:
    """セグメントプロファイルから N 体のエージェントを分布に従い生成する.

    new_drug_receptivity の分布に従い adoption_threshold を設定し、
    mr_contact の高い企業がある場合に KOL 比率を高める。
    """
    rng = random.Random(seed)
    agents: list[AgentProfile] = []

    ndr = profile.new_drug_receptivity

    # 受容性分布からカテゴリ別人数を算出
    categories = [
        ("early", ndr.early_prescriber, 0.8, 0.2),
        ("relatively_early", ndr.relatively_early, 0.65, 0.3),
        ("wait_and_see", ndr.wait_and_see, 0.5, 0.5),
        ("majority", ndr.majority_prescribes, 0.35, 0.65),
        ("after_established", ndr.after_established, 0.2, 0.8),
    ]

    # KOL 比率の推定（MR 面談カバー率が高い = KOL が多いセグメント）
    max_mr_rate = max(profile.mr_contact.values()) if profile.mr_contact else 0.3
    kol_ratio = min(0.15, max_mr_rate * 0.1)

    for _i in range(n):
        # 受容性カテゴリをランダム選択（分布に従う）
        weights = [c[1] for c in categories]
        total = sum(weights)
        if total == 0:
            weights = [0.2] * 5
            total = 1.0
        weights = [w / total for w in weights]

        cat_idx = rng.choices(range(len(categories)), weights=weights, k=1)[0]
        _, _, receptivity, threshold = categories[cat_idx]

        # ばらつきを追加
        receptivity += rng.gauss(0, 0.05)
        threshold += rng.gauss(0, 0.05)
        receptivity = max(0.05, min(0.95, receptivity))
        threshold = max(0.05, min(0.95, threshold))

        is_kol = rng.random() < kol_ratio

        agents.append(AgentProfile(
            specialty=profile.specialty,
            bed_size=profile.bed_size,
            age_range=profile.age_range,
            kol_score=0.9 if is_kol else rng.uniform(0.1, 0.5),
            receptivity=round(receptivity, 3),
            adoption_threshold=round(threshold, 3),
        ))

    return agents
