"""ABM 可視化 — ネットワークグラフとラインチャート.

設計書 W9 Day3-4 に対応。Plotly で採用状況のネットワーク可視化と
処方シェア変動の時系列チャートを生成する。
"""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from digital_twin.abm.physician_agent import AdoptionState, PhysicianAgent

# 採用状態ごとの色
_STATE_COLORS = {
    AdoptionState.NOT_ADOPTED: "#94A3B8",  # グレー
    AdoptionState.CONSIDERING: "#F59E0B",  # 黄色
    AdoptionState.ADOPTED: "#10B981",  # 緑
}

_STATE_LABELS = {
    AdoptionState.NOT_ADOPTED: "未採用",
    AdoptionState.CONSIDERING: "検討中",
    AdoptionState.ADOPTED: "採用済み",
}


def plot_network(
    agents: list[PhysicianAgent],
    network: nx.Graph,
    title: str = "医師ネットワーク — 採用状況",
) -> go.Figure:
    """ネットワークグラフを Plotly で生成する."""
    pos = nx.spring_layout(network, seed=42)

    # エッジ
    edge_x, edge_y = [], []
    for u, v in network.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line={"width": 0.5, "color": "#E2E8F0"},
        hoverinfo="none",
    )

    # ノード
    agent_map = {a.unique_id: a for a in agents}
    node_x, node_y, node_color, node_size, node_text = [], [], [], [], []

    for node_id in network.nodes():
        x, y = pos[node_id]
        agent = agent_map.get(node_id)
        if not agent:
            continue

        node_x.append(x)
        node_y.append(y)
        node_color.append(_STATE_COLORS.get(agent.state, "#94A3B8"))
        node_size.append(20 if agent.is_kol else 10)
        label = _STATE_LABELS.get(agent.state, "不明")
        node_text.append(
            f"ID: {agent.unique_id}<br>"
            f"診療科: {agent.profile.specialty}<br>"
            f"状態: {label}<br>"
            f"KOL: {'はい' if agent.is_kol else 'いいえ'}<br>"
            f"影響度: {agent.influence_accumulated:.3f}"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_text,
        marker={
            "size": node_size,
            "color": node_color,
            "line": {"width": 1, "color": "#fff"},
        },
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=title,
        showlegend=False,
        hovermode="closest",
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        height=500,
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )

    return fig


def plot_adoption_timeline(
    history: list[dict],
    event_steps: list[dict] | None = None,
    title: str = "採用率の時系列推移",
) -> go.Figure:
    """採用率の時系列ラインチャートを生成する."""
    steps = [h["step"] for h in history]
    rates = [h["adoption_rate"] for h in history]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=steps, y=rates,
        mode="lines+markers",
        name="採用率",
        line={"color": "#10B981", "width": 2},
        marker={"size": 4},
    ))

    # 状態別の積み上げエリア
    if history and "adopted" in history[0]:
        total = sum(history[0].get(s.value, 0) for s in AdoptionState)
        if total > 0:
            adopted = [h.get("adopted", 0) / total for h in history]
            considering = [h.get("considering", 0) / total for h in history]

            fig.add_trace(go.Scatter(
                x=steps, y=adopted,
                mode="lines", name="採用済み率",
                line={"color": "#10B981", "width": 1, "dash": "dot"},
            ))
            fig.add_trace(go.Scatter(
                x=steps, y=considering,
                mode="lines", name="検討中率",
                line={"color": "#F59E0B", "width": 1, "dash": "dot"},
            ))

    # イベントマーカー
    if event_steps:
        for evt in event_steps:
            fig.add_vline(
                x=evt["step"],
                line_dash="dash",
                line_color="#EF4444",
                annotation_text=evt.get("name", ""),
                annotation_position="top",
            )

    fig.update_layout(
        title=title,
        xaxis_title="タイムステップ",
        yaxis_title="割合",
        yaxis={"range": [0, 1]},
        height=400,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"x": 0.01, "y": 0.99},
    )

    return fig
