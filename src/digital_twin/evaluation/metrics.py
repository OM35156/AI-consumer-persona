"""Statistical comparison metrics for validating digital twin accuracy.

Compares simulated survey responses against actual responses to measure
how well the digital twin reproduces real respondent behavior.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
from scipy import stats
from scipy.spatial.distance import jensenshannon


@dataclass
class MetricResult:
    """Result of a single metric evaluation."""
    name: str
    value: float
    threshold: float
    passed: bool
    details: str = ""

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"{self.name}: {self.value:.4f} (threshold: {self.threshold}) [{status}]"


@dataclass
class ValidationReport:
    """Complete validation report across all metrics."""
    metrics: list[MetricResult]
    n_questions: int
    n_respondents: int

    @property
    def overall_pass(self) -> bool:
        return all(m.passed for m in self.metrics)

    @property
    def pass_rate(self) -> float:
        if not self.metrics:
            return 0.0
        return sum(1 for m in self.metrics if m.passed) / len(self.metrics)

    def summary(self) -> str:
        lines = [
            "=== Validation Report ===",
            f"Respondents: {self.n_respondents}",
            f"Questions: {self.n_questions}",
            f"Overall: {'PASS' if self.overall_pass else 'FAIL'} ({self.pass_rate:.0%} metrics passed)",
            "",
        ]
        for m in self.metrics:
            lines.append(f"  {m}")
        return "\n".join(lines)


def js_divergence(
    real_responses: list[str | int],
    simulated_responses: list[str | int],
    threshold: float = 0.10,
) -> MetricResult:
    """Jensen-Shannon divergence between response distributions.

    Lower is better. 0 = identical distributions.
    """
    all_values = sorted(set(real_responses) | set(simulated_responses))
    if not all_values:
        return MetricResult("JS Divergence", 0.0, threshold, True, "No data")

    real_counts = Counter(real_responses)
    sim_counts = Counter(simulated_responses)

    # Convert to probability distributions
    real_dist = np.array([real_counts.get(v, 0) for v in all_values], dtype=float)
    sim_dist = np.array([sim_counts.get(v, 0) for v in all_values], dtype=float)

    # Normalize
    real_dist = real_dist / real_dist.sum() if real_dist.sum() > 0 else real_dist
    sim_dist = sim_dist / sim_dist.sum() if sim_dist.sum() > 0 else sim_dist

    js = float(jensenshannon(real_dist, sim_dist))

    return MetricResult(
        name="JS Divergence",
        value=js,
        threshold=threshold,
        passed=js <= threshold,
        details=f"Real dist: {dict(zip(all_values, real_dist.round(3), strict=False))}"
    )


def mode_agreement(
    real_responses: dict[str, list],
    simulated_responses: dict[str, list],
    threshold: float = 0.70,
) -> MetricResult:
    """Per-question mode agreement rate.

    Checks if the most common response matches between real and simulated.
    """
    agreements = 0
    total = 0

    for qid in real_responses:
        if qid not in simulated_responses:
            continue

        real_mode = Counter(real_responses[qid]).most_common(1)
        sim_mode = Counter(simulated_responses[qid]).most_common(1)

        if real_mode and sim_mode:
            total += 1
            if real_mode[0][0] == sim_mode[0][0]:
                agreements += 1

    rate = agreements / total if total > 0 else 0.0

    return MetricResult(
        name="Mode Agreement",
        value=rate,
        threshold=threshold,
        passed=rate >= threshold,
        details=f"{agreements}/{total} questions matched",
    )


def spearman_rank_correlation(
    real_responses: list[str | int],
    simulated_responses: list[str | int],
    value_order: list[str | int] | None = None,
    threshold: float = 0.80,
) -> MetricResult:
    """Spearman rank correlation for ordinal responses.

    Measures if item rankings match between real and simulated distributions.
    """
    all_values = value_order or sorted(set(real_responses) | set(simulated_responses))

    real_counts = Counter(real_responses)
    sim_counts = Counter(simulated_responses)

    real_ranks = [real_counts.get(v, 0) for v in all_values]
    sim_ranks = [sim_counts.get(v, 0) for v in all_values]

    if len(all_values) < 3:
        return MetricResult(
            "Spearman Correlation", 1.0, threshold, True, "Too few values"
        )

    rho, _ = stats.spearmanr(real_ranks, sim_ranks)

    return MetricResult(
        name="Spearman Correlation",
        value=float(rho) if not np.isnan(rho) else 0.0,
        threshold=threshold,
        passed=float(rho) >= threshold if not np.isnan(rho) else False,
    )


def chi_square_test(
    real_responses: list[str | int],
    simulated_responses: list[str | int],
    p_threshold: float = 0.05,
) -> MetricResult:
    """Chi-square test for distribution independence.

    p > threshold means no significant difference (PASS).
    """
    all_values = sorted(set(real_responses) | set(simulated_responses))

    real_counts = Counter(real_responses)
    sim_counts = Counter(simulated_responses)

    observed = np.array([real_counts.get(v, 0) for v in all_values])
    expected = np.array([sim_counts.get(v, 0) for v in all_values])

    # Normalize expected to have same total as observed
    if expected.sum() > 0:
        expected = expected * (observed.sum() / expected.sum())

    # Filter out zero-expected cells
    mask = expected > 0
    if mask.sum() < 2:
        return MetricResult("Chi-Square Test", 1.0, p_threshold, True, "Insufficient data")

    chi2, p_value = stats.chisquare(observed[mask], expected[mask])

    return MetricResult(
        name="Chi-Square Test (p-value)",
        value=float(p_value),
        threshold=p_threshold,
        passed=float(p_value) >= p_threshold,
        details=f"chi2={chi2:.2f}, p={p_value:.4f}",
    )


def effect_direction_consistency(
    real_responses: dict[str, dict[str, list]],
    simulated_responses: dict[str, dict[str, list]],
    threshold: float = 0.90,
) -> MetricResult:
    """Check if subgroup differences have the same direction.

    For each question, checks if the difference between subgroups
    (e.g., male vs female) goes in the same direction for real and simulated.
    """
    consistent = 0
    total = 0

    for qid in real_responses:
        if qid not in simulated_responses:
            continue

        real_groups = real_responses[qid]
        sim_groups = simulated_responses[qid]

        group_keys = list(set(real_groups.keys()) & set(sim_groups.keys()))
        if len(group_keys) < 2:
            continue

        for i in range(len(group_keys)):
            for j in range(i + 1, len(group_keys)):
                g1, g2 = group_keys[i], group_keys[j]
                real_diff = _mean_or_mode(real_groups[g1]) - _mean_or_mode(real_groups[g2])
                sim_diff = _mean_or_mode(sim_groups[g1]) - _mean_or_mode(sim_groups[g2])

                total += 1
                if (real_diff > 0 and sim_diff > 0) or (real_diff <= 0 and sim_diff <= 0):
                    consistent += 1

    rate = consistent / total if total > 0 else 1.0

    return MetricResult(
        name="Effect Direction Consistency",
        value=rate,
        threshold=threshold,
        passed=rate >= threshold,
        details=f"{consistent}/{total} subgroup comparisons consistent",
    )


def _mean_or_mode(values: list) -> float:
    """Return mean for numeric, mode index for categorical."""
    if not values:
        return 0.0
    if isinstance(values[0], (int, float)):
        return float(np.mean(values))
    # For categorical, return the index of the mode
    mode = Counter(values).most_common(1)[0][0]
    return float(hash(str(mode)) % 100)  # Deterministic numeric proxy
