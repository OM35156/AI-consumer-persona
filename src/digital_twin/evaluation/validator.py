"""Holdout-based validation pipeline.

Validates digital twins by:
1. Building personas from Survey A responses
2. Simulating Survey B responses
3. Comparing simulated vs actual Survey B responses
"""

from __future__ import annotations

import logging
from collections import defaultdict

from digital_twin.data.schema import Physician
from digital_twin.engine.simulator import SurveySimResult
from digital_twin.evaluation.metrics import (
    MetricResult,
    ValidationReport,
    chi_square_test,
    js_divergence,
    mode_agreement,
    spearman_rank_correlation,
)

logger = logging.getLogger(__name__)


def extract_responses_by_question(
    respondents: list[Physician],
    survey_id: str,
) -> dict[str, list]:
    """Extract actual responses grouped by question ID.

    Returns:
        Dict mapping question_id -> list of response values.
    """
    by_question: dict[str, list] = defaultdict(list)

    for r in respondents:
        for sr in r.survey_responses:
            if sr.survey_id != survey_id:
                continue
            for qr in sr.responses:
                if qr.response_value is not None:
                    by_question[qr.question_id].append(qr.response_value)
                elif qr.free_text is not None:
                    by_question[qr.question_id].append(qr.free_text)

    return dict(by_question)


def extract_simulated_by_question(
    results: list[SurveySimResult],
) -> dict[str, list]:
    """Extract simulated responses grouped by question ID.

    Aggregates across replications.
    """
    by_question: dict[str, list] = defaultdict(list)

    for r in results:
        for qid, value in r.responses.items():
            by_question[qid].append(value)

    return dict(by_question)


def validate(
    real_respondents: list[Physician],
    simulation_results: list[SurveySimResult],
    validation_survey_id: str,
    js_threshold: float = 0.10,
    mode_threshold: float = 0.70,
    spearman_threshold: float = 0.80,
    chi_sq_threshold: float = 0.05,
) -> ValidationReport:
    """Run the full validation pipeline.

    Args:
        real_respondents: Holdout respondents with actual Survey B responses.
        simulation_results: Simulated responses from the engine.
        validation_survey_id: The survey ID used for validation (Survey B).
        js_threshold: Jensen-Shannon divergence threshold.
        mode_threshold: Mode agreement threshold.
        spearman_threshold: Spearman correlation threshold.
        chi_sq_threshold: Chi-square p-value threshold.

    Returns:
        ValidationReport with all metric results.
    """
    real_by_q = extract_responses_by_question(real_respondents, validation_survey_id)
    sim_by_q = extract_simulated_by_question(simulation_results)

    metrics: list[MetricResult] = []
    question_ids = sorted(set(real_by_q.keys()) & set(sim_by_q.keys()))

    if not question_ids:
        logger.warning("No overlapping questions between real and simulated data")
        return ValidationReport(metrics=[], n_questions=0, n_respondents=len(real_respondents))

    # 1. JS Divergence (per question, then average)
    js_values = []
    for qid in question_ids:
        real_flat = _flatten_responses(real_by_q[qid])
        sim_flat = _flatten_responses(sim_by_q[qid])
        if real_flat and sim_flat:
            result = js_divergence(real_flat, sim_flat, js_threshold)
            js_values.append(result.value)

    if js_values:
        avg_js = sum(js_values) / len(js_values)
        metrics.append(
            MetricResult(
                name="Avg JS Divergence",
                value=avg_js,
                threshold=js_threshold,
                passed=avg_js <= js_threshold,
                details=f"Across {len(js_values)} questions",
            )
        )

    # 2. Mode Agreement
    real_flat_by_q = {qid: _flatten_responses(real_by_q[qid]) for qid in question_ids}
    sim_flat_by_q = {qid: _flatten_responses(sim_by_q[qid]) for qid in question_ids}
    metrics.append(mode_agreement(real_flat_by_q, sim_flat_by_q, mode_threshold))

    # 3. Spearman Correlation (per question, averaged)
    spearman_values = []
    for qid in question_ids:
        real_flat = _flatten_responses(real_by_q[qid])
        sim_flat = _flatten_responses(sim_by_q[qid])
        if real_flat and sim_flat and len(set(real_flat)) >= 3:
            result = spearman_rank_correlation(real_flat, sim_flat, threshold=spearman_threshold)
            spearman_values.append(result.value)

    if spearman_values:
        avg_spearman = sum(spearman_values) / len(spearman_values)
        metrics.append(
            MetricResult(
                name="Avg Spearman Correlation",
                value=avg_spearman,
                threshold=spearman_threshold,
                passed=avg_spearman >= spearman_threshold,
                details=f"Across {len(spearman_values)} ordinal questions",
            )
        )

    # 4. Chi-Square Test (per question, report worst)
    chi_p_values = []
    for qid in question_ids:
        real_flat = _flatten_responses(real_by_q[qid])
        sim_flat = _flatten_responses(sim_by_q[qid])
        if real_flat and sim_flat:
            result = chi_square_test(real_flat, sim_flat, chi_sq_threshold)
            chi_p_values.append(result.value)

    if chi_p_values:
        min_p = min(chi_p_values)
        metrics.append(
            MetricResult(
                name="Worst Chi-Square p-value",
                value=min_p,
                threshold=chi_sq_threshold,
                passed=min_p >= chi_sq_threshold,
                details=f"Worst across {len(chi_p_values)} questions",
            )
        )

    return ValidationReport(
        metrics=metrics,
        n_questions=len(question_ids),
        n_respondents=len(real_respondents),
    )


def _flatten_responses(values: list) -> list[str]:
    """Flatten list responses and convert to strings for comparison."""
    flat = []
    for v in values:
        if isinstance(v, list):
            flat.extend(str(x) for x in v)
        else:
            flat.append(str(v))
    return flat
