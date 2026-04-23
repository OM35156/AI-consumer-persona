"""ABM 可視化 — ネットワークグラフとラインチャート.

5段階ファネル（未認知→認知→関心→購買→リピート）の
ネットワーク可視化と浸透推移チャートを生成する。
"""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from digital_twin.abm.consumer_agent import AdoptionState, ConsumerAgent

# 採用状態ごとの色
_STATE_COLORS = {
    AdoptionState.UNAWARE: "#94A3B8",      # グレー
    AdoptionState.AWARE: "#60A5FA",        # 青
    AdoptionState.INTERESTED: "#F59E0B",   # 黄
    AdoptionState.PURCHASED: "#10B981",    # 緑
    AdoptionState.REPEAT: "#8B5CF6",       # 紫
}

_STATE_LABELS = {
    AdoptionState.UNAWARE: "未認知",
    AdoptionState.AWARE: "認知",
    AdoptionState.INTERESTED: "関心",
    AdoptionState.PURCHASED: "購買",
    AdoptionState.REPEAT: "リピート",
}


def plot_network(
    agents: list[ConsumerAgent],
    network: nx.Graph,
    title: str = "生活者ネットワーク — 浸透状況",
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
        node_size.append(20 if agent.is_influencer else 10)
        label = _STATE_LABELS.get(agent.state, "不明")
        node_text.append(
            f"ID: {agent.unique_id}<br>"
            f"関心カテゴリ: {agent.profile.category}<br>"
            f"状態: {label}<br>"
            f"インフルエンサー: {'はい' if agent.is_influencer else 'いいえ'}<br>"
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
    title: str = "商品浸透ファネル推移",
) -> go.Figure:
    """ファネル各段階の時系列ラインチャートを生成する."""
    steps = [h["step"] for h in history]

    fig = go.Figure()

    # 各状態の割合を計算して表示
    state_configs = [
        ("aware", "認知", "#60A5FA"),
        ("interested", "関心", "#F59E0B"),
        ("purchased", "購買", "#10B981"),
        ("repeat", "リピート", "#8B5CF6"),
    ]

    for state_key, label, color in state_configs:
        if history and state_key in history[0]:
            total = sum(history[0].get(s.value, 0) for s in AdoptionState)
            if total > 0:
                # 累積: その段階以上に到達した人の割合
                if state_key == "aware":
                    values = [
                        (h.get("aware", 0) + h.get("interested", 0) + h.get("purchased", 0) + h.get("repeat", 0)) / total
                        for h in history
                    ]
                elif state_key == "interested":
                    values = [
                        (h.get("interested", 0) + h.get("purchased", 0) + h.get("repeat", 0)) / total
                        for h in history
                    ]
                elif state_key == "purchased":
                    values = [
                        (h.get("purchased", 0) + h.get("repeat", 0)) / total
                        for h in history
                    ]
                else:  # repeat
                    values = [h.get("repeat", 0) / total for h in history]

                fig.add_trace(go.Scatter(
                    x=steps, y=values,
                    mode="lines",
                    name=f"{label}到達率",
                    line={"color": color, "width": 2},
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
        xaxis_title="タイムステップ（月）",
        yaxis_title="到達率",
        yaxis={"range": [0, 1]},
        height=400,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"x": 0.01, "y": 0.99},
    )

    return fig
