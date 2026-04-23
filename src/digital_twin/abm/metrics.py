"""ABM 拡張メトリクス — ビジネス判断に必要な指標を算出する.

ファネル各段階（認知→関心→購買→リピート）の到達率、
time-to-purchase、拡散速度等を計算する。
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from digital_twin.abm.consumer_agent import AdoptionState, ConsumerAgent

logger = logging.getLogger(__name__)

# 購買到達とみなす状態
_PURCHASED_STATES = {AdoptionState.PURCHASED, AdoptionState.REPEAT}


@dataclass
class ABMMetrics:
    """ABM シミュレーションの拡張メトリクス."""

    total_agents: int = 0
    # ファネル各段階の到達数
    aware_count: int = 0
    interested_count: int = 0
    purchased_count: int = 0
    repeat_count: int = 0
    # ファネル到達率
    funnel_rates: dict[str, float] = field(default_factory=dict)
    # 購買関連
    final_purchase_rate: float = 0.0
    mean_time_to_purchase: float = 0.0
    median_time_to_purchase: float = 0.0
    diffusion_speed: list[int] = field(default_factory=list)
    adoption_by_category: dict[str, float] = field(default_factory=dict)
    influencer_purchase_rate: float = 0.0
    non_influencer_purchase_rate: float = 0.0


def calculate_metrics(
    agents: list[ConsumerAgent],
    history: list[dict],
) -> ABMMetrics:
    """エージェントと実行履歴から拡張メトリクスを算出する."""
    total = len(agents)

    # ファネル各段階のカウント（その段階以上に到達した人数）
    aware = [a for a in agents if a.state != AdoptionState.UNAWARE]
    interested = [a for a in agents if a.state in {
        AdoptionState.INTERESTED, AdoptionState.PURCHASED, AdoptionState.REPEAT,
    }]
    purchased = [a for a in agents if a.state in _PURCHASED_STATES]
    repeat = [a for a in agents if a.state == AdoptionState.REPEAT]

    # time-to-purchase
    purchase_times = [a.adoption_step for a in purchased if a.adoption_step is not None]
    mean_ttp = sum(purchase_times) / len(purchase_times) if purchase_times else 0.0
    sorted_times = sorted(purchase_times)
    median_ttp = sorted_times[len(sorted_times) // 2] if sorted_times else 0.0

    # 拡散速度（ステップごとの新規購買数）
    diffusion = []
    prev_purchased = 0
    for h in history:
        current = h.get("purchased", 0) + h.get("repeat", 0)
        diffusion.append(current - prev_purchased)
        prev_purchased = current

    # カテゴリ別購買率
    category_counts: dict[str, list[int]] = {}
    for a in agents:
        cat = a.profile.category
        if cat not in category_counts:
            category_counts[cat] = [0, 0]
        category_counts[cat][0] += 1
        if a.state in _PURCHASED_STATES:
            category_counts[cat][1] += 1
    adoption_by_cat = {
        cat: counts[1] / counts[0] if counts[0] > 0 else 0.0
        for cat, counts in category_counts.items()
    }

    # インフルエンサー vs 非インフルエンサー
    influencers = [a for a in agents if a.is_influencer]
    non_influencers = [a for a in agents if not a.is_influencer]
    infl_rate = (
        sum(1 for a in influencers if a.state in _PURCHASED_STATES) / len(influencers)
        if influencers else 0.0
    )
    non_infl_rate = (
        sum(1 for a in non_influencers if a.state in _PURCHASED_STATES) / len(non_influencers)
        if non_influencers else 0.0
    )

    funnel_rates = {}
    if total > 0:
        funnel_rates = {
            "認知率": len(aware) / total,
            "関心率": len(interested) / total,
            "購買率": len(purchased) / total,
            "リピート率": len(repeat) / total,
        }

    return ABMMetrics(
        total_agents=total,
        aware_count=len(aware),
        interested_count=len(interested),
        purchased_count=len(purchased),
        repeat_count=len(repeat),
        funnel_rates=funnel_rates,
        final_purchase_rate=len(purchased) / total if total > 0 else 0.0,
        mean_time_to_purchase=mean_ttp,
        median_time_to_purchase=median_ttp,
        diffusion_speed=diffusion,
        adoption_by_category=adoption_by_cat,
        influencer_purchase_rate=infl_rate,
        non_influencer_purchase_rate=non_infl_rate,
    )


def export_history_csv(history: list[dict], output_path: str | Path) -> None:
    """シミュレーション履歴を CSV にエクスポートする."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not history:
        return

    fieldnames = list(history[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history)

    logger.info(f"履歴エクスポート: {output_path}")


def export_metrics_json(metrics: ABMMetrics, output_path: str | Path) -> None:
    """メトリクスを JSON にエクスポートする."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_agents": metrics.total_agents,
        "funnel_rates": {k: round(v, 4) for k, v in metrics.funnel_rates.items()},
        "final_purchase_rate": round(metrics.final_purchase_rate, 4),
        "mean_time_to_purchase": round(metrics.mean_time_to_purchase, 2),
        "median_time_to_purchase": metrics.median_time_to_purchase,
        "adoption_by_category": {k: round(v, 4) for k, v in metrics.adoption_by_category.items()},
        "influencer_purchase_rate": round(metrics.influencer_purchase_rate, 4),
        "non_influencer_purchase_rate": round(metrics.non_influencer_purchase_rate, 4),
        "peak_diffusion_speed": max(metrics.diffusion_speed) if metrics.diffusion_speed else 0,
    }

    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"メトリクスエクスポート: {output_path}")
