"""Visualization utilities for comparing real vs simulated responses."""

from __future__ import annotations

from collections import Counter

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_distribution_comparison(
    real_responses: list[str],
    simulated_responses: list[str],
    question_text: str,
    question_id: str = "",
) -> go.Figure:
    """Create a side-by-side bar chart comparing response distributions."""
    all_values = sorted(set(real_responses) | set(simulated_responses))

    real_counts = Counter(real_responses)
    sim_counts = Counter(simulated_responses)

    real_pcts = [real_counts.get(v, 0) / len(real_responses) * 100 for v in all_values]
    sim_pcts = [sim_counts.get(v, 0) / len(simulated_responses) * 100 for v in all_values]

    fig = go.Figure(data=[
        go.Bar(name="実データ", x=all_values, y=real_pcts, marker_color="#2E86AB"),
        go.Bar(name="シミュレーション", x=all_values, y=sim_pcts, marker_color="#F18F01"),
    ])

    title = f"{question_id}: {question_text}" if question_id else question_text
    fig.update_layout(
        title=title,
        xaxis_title="回答",
        yaxis_title="割合 (%)",
        barmode="group",
        template="plotly_white",
        legend=dict(x=0.7, y=1.0),
    )

    return fig


def plot_metrics_dashboard(
    metrics: list[dict],
) -> go.Figure:
    """Create a dashboard showing all validation metrics."""
    names = [m["name"] for m in metrics]
    values = [m["value"] for m in metrics]
    thresholds = [m["threshold"] for m in metrics]
    passed = [m["passed"] for m in metrics]

    colors = ["#2E86AB" if p else "#E63946" for p in passed]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=names,
        y=values,
        marker_color=colors,
        name="値",
        text=[f"{v:.3f}" for v in values],
        textposition="outside",
    ))

    fig.add_trace(go.Scatter(
        x=names,
        y=thresholds,
        mode="markers+lines",
        marker=dict(size=12, symbol="line-ew-open", color="red"),
        line=dict(dash="dash", color="red"),
        name="閾値",
    ))

    fig.update_layout(
        title="検証指標ダッシュボード",
        yaxis_title="値",
        template="plotly_white",
        showlegend=True,
    )

    return fig


def plot_multi_question_comparison(
    real_by_question: dict[str, list[str]],
    simulated_by_question: dict[str, list[str]],
    question_texts: dict[str, str],
) -> go.Figure:
    """Create a grid of distribution comparisons for multiple questions."""
    question_ids = sorted(
        set(real_by_question.keys()) & set(simulated_by_question.keys())
    )

    n = len(question_ids)
    if n == 0:
        return go.Figure()

    cols = min(2, n)
    rows = (n + cols - 1) // cols

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[
            f"{qid}: {question_texts.get(qid, '')[:30]}" for qid in question_ids
        ],
    )

    for i, qid in enumerate(question_ids):
        row = i // cols + 1
        col = i % cols + 1

        all_values = sorted(
            set(real_by_question[qid]) | set(simulated_by_question[qid])
        )
        real_counts = Counter(real_by_question[qid])
        sim_counts = Counter(simulated_by_question[qid])

        n_real = len(real_by_question[qid])
        n_sim = len(simulated_by_question[qid])

        real_pcts = [real_counts.get(v, 0) / n_real * 100 for v in all_values]
        sim_pcts = [sim_counts.get(v, 0) / n_sim * 100 for v in all_values]

        fig.add_trace(
            go.Bar(x=all_values, y=real_pcts, name="実データ",
                   marker_color="#2E86AB", showlegend=(i == 0)),
            row=row, col=col,
        )
        fig.add_trace(
            go.Bar(x=all_values, y=sim_pcts, name="シミュレーション",
                   marker_color="#F18F01", showlegend=(i == 0)),
            row=row, col=col,
        )

    fig.update_layout(
        height=400 * rows,
        title_text="設問別 回答分布比較",
        barmode="group",
        template="plotly_white",
    )

    return fig
