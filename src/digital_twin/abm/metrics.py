"""ABM 拡張メトリクス — ビジネス判断に必要な指標を算出する.

採用率だけでなく、time-to-adoption、診療科別推移、拡散速度等を計算する。
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from digital_twin.abm.consumer_agent import AdoptionState, ConsumerAgent

logger = logging.getLogger(__name__)


@dataclass
class ABMMetrics:
    """ABM シミュレーションの拡張メトリクス."""

    total_agents: int = 0
    total_adopted: int = 0
    final_adoption_rate: float = 0.0
    mean_time_to_adoption: float = 0.0
    median_time_to_adoption: float = 0.0
    diffusion_speed: list[int] = field(default_factory=list)  # ステップごとの新規採用数
    adoption_by_specialty: dict[str, float] = field(default_factory=dict)
    kol_adoption_rate: float = 0.0
    non_kol_adoption_rate: float = 0.0


def calculate_metrics(
    agents: list[ConsumerAgent],
    history: list[dict],
) -> ABMMetrics:
    """エージェントと実行履歴から拡張メトリクスを算出する."""
    total = len(agents)
    adopted = [a for a in agents if a.state == AdoptionState.ADOPTED]

    # time-to-adoption
    adoption_times = [a.adoption_step for a in adopted if a.adoption_step is not None]
    mean_tta = sum(adoption_times) / len(adoption_times) if adoption_times else 0.0
    sorted_times = sorted(adoption_times)
    median_tta = sorted_times[len(sorted_times) // 2] if sorted_times else 0.0

    # 拡散速度（ステップごとの新規採用数）
    diffusion = []
    prev_adopted = 0
    for h in history:
        current = h.get("adopted", 0)
        diffusion.append(current - prev_adopted)
        prev_adopted = current

    # 診療科別採用率
    specialty_counts: dict[str, list[int]] = {}
    for a in agents:
        spec = a.profile.specialty
        if spec not in specialty_counts:
            specialty_counts[spec] = [0, 0]
        specialty_counts[spec][0] += 1
        if a.state == AdoptionState.ADOPTED:
            specialty_counts[spec][1] += 1
    adoption_by_spec = {
        spec: counts[1] / counts[0] if counts[0] > 0 else 0.0
        for spec, counts in specialty_counts.items()
    }

    # KOL vs 非KOL
    kols = [a for a in agents if a.is_influencer]
    non_kols = [a for a in agents if not a.is_influencer]
    kol_rate = sum(1 for a in kols if a.state == AdoptionState.ADOPTED) / len(kols) if kols else 0.0
    non_kol_rate = sum(1 for a in non_kols if a.state == AdoptionState.ADOPTED) / len(non_kols) if non_kols else 0.0

    return ABMMetrics(
        total_agents=total,
        total_adopted=len(adopted),
        final_adoption_rate=len(adopted) / total if total > 0 else 0.0,
        mean_time_to_adoption=mean_tta,
        median_time_to_adoption=median_tta,
        diffusion_speed=diffusion,
        adoption_by_specialty=adoption_by_spec,
        kol_adoption_rate=kol_rate,
        non_kol_adoption_rate=non_kol_rate,
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
        "total_adopted": metrics.total_adopted,
        "final_adoption_rate": round(metrics.final_adoption_rate, 4),
        "mean_time_to_adoption": round(metrics.mean_time_to_adoption, 2),
        "median_time_to_adoption": metrics.median_time_to_adoption,
        "adoption_by_specialty": {k: round(v, 4) for k, v in metrics.adoption_by_specialty.items()},
        "kol_adoption_rate": round(metrics.kol_adoption_rate, 4),
        "non_kol_adoption_rate": round(metrics.non_kol_adoption_rate, 4),
        "peak_diffusion_speed": max(metrics.diffusion_speed) if metrics.diffusion_speed else 0,
    }

    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"メトリクスエクスポート: {output_path}")
