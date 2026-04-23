"""ABM キャリブレーション — 実データとシミュレーションの突合・パラメータ最適化.

過去の実際の採用曲線（Impact Track の処方意向推移）と
シミュレーション結果を突合し、パラメータを調整する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from scipy import optimize

from digital_twin.abm.consumer_agent import AdoptionState, AgentProfile
from digital_twin.abm.model import PrescriptionModel

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """キャリブレーション結果."""

    rmse: float = 0.0
    js_divergence: float = 0.0
    max_error: float = 0.0
    correlation: float = 0.0
    optimal_params: dict[str, float] = field(default_factory=dict)


def compute_rmse(real_curve: list[float], sim_curve: list[float]) -> float:
    """実データとシミュレーションの RMSE を計算する."""
    n = min(len(real_curve), len(sim_curve))
    if n == 0:
        return 0.0
    real = np.array(real_curve[:n])
    sim = np.array(sim_curve[:n])
    return float(np.sqrt(np.mean((real - sim) ** 2)))


def compute_correlation(real_curve: list[float], sim_curve: list[float]) -> float:
    """実データとシミュレーションの相関係数を計算する."""
    n = min(len(real_curve), len(sim_curve))
    if n < 3:
        return 0.0
    real = np.array(real_curve[:n])
    sim = np.array(sim_curve[:n])
    if np.std(real) == 0 or np.std(sim) == 0:
        return 0.0
    return float(np.corrcoef(real, sim)[0, 1])


def calibrate(
    real_adoption_curve: list[float],
    agent_profiles: list[AgentProfile],
    n_initial_adopters: int = 3,
    seed: int = 42,
) -> CalibrationResult:
    """実データの採用曲線とシミュレーションを突合する."""
    steps = len(real_adoption_curve)
    if steps == 0:
        return CalibrationResult()

    # デフォルトパラメータでシミュレーション
    sim_curve = _run_simulation(agent_profiles, n_initial_adopters, steps, seed=seed)

    rmse = compute_rmse(real_adoption_curve, sim_curve)
    corr = compute_correlation(real_adoption_curve, sim_curve)
    max_err = float(max(abs(r - s) for r, s in zip(real_adoption_curve, sim_curve, strict=False)))

    return CalibrationResult(
        rmse=rmse,
        correlation=corr,
        max_error=max_err,
    )


def sensitivity_analysis(
    agent_profiles: list[AgentProfile],
    param_name: str,
    param_range: list[float],
    steps: int = 30,
    n_initial_adopters: int = 3,
    seed: int = 42,
) -> list[dict]:
    """パラメータ感度分析 — 1つのパラメータを変化させた時の採用率推移.

    Args:
        param_name: "kol_influence" / "peer_influence" / "decay_rate"
        param_range: パラメータ値のリスト
    """
    results = []
    for value in param_range:
        kwargs = {param_name: value} if param_name in ("kol_influence", "peer_influence") else {}
        curve = _run_simulation(agent_profiles, n_initial_adopters, steps, seed=seed, **kwargs)
        results.append({
            "param_value": value,
            "final_purchase_rate": curve[-1] if curve else 0.0,
            "curve": curve,
        })
    return results


def optimize_parameters(
    real_adoption_curve: list[float],
    agent_profiles: list[AgentProfile],
    n_initial_adopters: int = 3,
    seed: int = 42,
) -> CalibrationResult:
    """scipy.optimize で最適パラメータを探索する."""
    steps = len(real_adoption_curve)
    if steps == 0:
        return CalibrationResult()

    real = np.array(real_adoption_curve)

    def objective(params: np.ndarray) -> float:
        kol_inf, peer_inf = params
        sim = _run_simulation(
            agent_profiles, n_initial_adopters, steps,
            seed=seed, kol_influence=float(kol_inf), peer_influence=float(peer_inf),
        )
        return float(np.sqrt(np.mean((real - np.array(sim)) ** 2)))

    result = optimize.minimize(
        objective,
        x0=[0.15, 0.05],
        bounds=[(0.01, 0.5), (0.005, 0.2)],
        method="Nelder-Mead",
    )

    optimal_kol, optimal_peer = result.x
    sim_curve = _run_simulation(
        agent_profiles, n_initial_adopters, steps,
        seed=seed, kol_influence=float(optimal_kol), peer_influence=float(optimal_peer),
    )

    return CalibrationResult(
        rmse=float(result.fun),
        correlation=compute_correlation(real_adoption_curve, sim_curve),
        max_error=float(max(abs(r - s) for r, s in zip(real_adoption_curve, sim_curve, strict=False))),
        optimal_params={"kol_influence": round(float(optimal_kol), 4), "peer_influence": round(float(optimal_peer), 4)},
    )


def _run_simulation(
    agent_profiles: list[AgentProfile],
    n_initial_adopters: int,
    steps: int,
    seed: int = 42,
    kol_influence: float = 0.15,
    peer_influence: float = 0.05,
) -> list[float]:
    """シミュレーションを実行し、採用率の時系列を返す."""
    model = PrescriptionModel(
        agent_profiles, seed=seed,
        kol_influence=kol_influence, peer_influence=peer_influence,
    )
    for i in range(min(n_initial_adopters, len(model.consumer_agents))):
        model.consumer_agents[i].state = AdoptionState.PURCHASED
        model.consumer_agents[i].adoption_step = 0

    history = model.run(steps=steps)
    return [h["purchase_rate"] for h in history]
