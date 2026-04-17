"""生活者 AI ペルソナ — 睡眠インタビューシミュレーター."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[3]
load_dotenv(project_root / ".env")
sys.path.insert(0, str(project_root / "src"))

from digital_twin.data.schema import Consumer, SleepConcern  # noqa: E402
from digital_twin.engine.sleep_prompt import render_sleep_interview_prompt  # noqa: E402
from digital_twin.persona.builder import ConsumerPersonaBuilder  # noqa: E402
from digital_twin.persona.profile import (  # noqa: E402
    ConsumerPersona,
    _life_stage_ja,
    _region_ja,
)

st.set_page_config(page_title="生活者AIペルソナ", page_icon="🌙", layout="wide")

# ── Colors ──
NAVY = "#0B1929"
ACCENT = "#2E86AB"
GOLD = "#C4A35A"
GREEN = "#10B981"
WARN = "#F59E0B"

_CONCERN_JA = {
    "difficulty_falling_asleep": "入眠困難",
    "midnight_awakening": "中途覚醒",
    "early_awakening": "早朝覚醒",
    "poor_quality": "熟眠感不足",
    "short_duration": "睡眠時間不足",
    "daytime_sleepiness": "日中の眠気",
    "none": "特になし",
}

_PRODUCT_JA = {
    "supplement": "サプリ",
    "mattress": "マットレス",
    "pillow": "枕",
    "pajamas": "パジャマ",
    "aroma": "アロマ",
    "app": "睡眠アプリ",
    "prescription": "処方薬",
}


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


# ── Global CSS ──
html("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter','Noto Sans JP',sans-serif; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0B1929,#132D4A); }
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
#MainMenu, footer { visibility: hidden; }
.stTabs [data-baseweb="tab-list"] { background: #fff; border-radius: 12px; padding: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.stTabs [aria-selected="true"] { background: #0B1929 !important; color: white !important; border-radius: 10px; }
</style>""")


# ══════════════════════════════════════
# Data Loading
# ══════════════════════════════════════


@st.cache_data
def load_synthetic_data(json_path: str) -> list[Consumer]:
    """合成データ JSON を Consumer リストとして読み込む."""
    raw = json.loads(Path(json_path).read_text(encoding="utf-8"))
    return [Consumer.model_validate(r) for r in raw]


@st.cache_data
def build_personas(consumers_json: str) -> list[ConsumerPersona]:
    """Consumer リストからペルソナを構築する."""
    consumers = load_synthetic_data(consumers_json)
    builder = ConsumerPersonaBuilder(seed=42)
    return builder.build_batch(consumers)


# ══════════════════════════════════════
# Sidebar
# ══════════════════════════════════════


def sidebar() -> tuple[list[Consumer], list[ConsumerPersona]] | None:
    with st.sidebar:
        html(
            f'<div style="text-align:center;padding:20px 0 10px">'
            f'<div style="font-size:1.5rem;font-weight:700;color:white">生活者AIペルソナ</div>'
            f'<div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;'
            f'letter-spacing:0.1em;margin-top:4px">Sleep Interview Simulator</div>'
            f'</div><hr style="border-color:rgba(255,255,255,0.08);margin:12px 0 20px">'
        )

        default_path = str(project_root / "data" / "synthetic" / "sleep_consumers_v1.json")
        data_path = st.text_input("JSON データパス", value=default_path, label_visibility="collapsed")

        if not Path(data_path).exists():
            st.error("データが見つかりません。合成データを生成してください:")
            st.code(
                "uv run python scripts/synth/generate_sleep_consumers.py --n 300 --seed 42",
                language="bash",
            )
            return None

        consumers = load_synthetic_data(data_path)
        personas = build_personas(data_path)

        n = len(consumers)
        n_with_concerns = sum(
            1 for c in consumers
            if c.sleep_profile and c.sleep_profile.concerns != [SleepConcern.NONE]
        )

        html(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:16px 0">'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center">'
            f'<div style="font-size:1.4rem;font-weight:700;color:white">{n}</div>'
            f'<div style="font-size:0.65rem;color:#94A3B8">生活者数</div></div>'
            f'<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center">'
            f'<div style="font-size:1.4rem;font-weight:700;color:{WARN}">{n_with_concerns}</div>'
            f'<div style="font-size:0.65rem;color:#94A3B8">睡眠悩みあり</div></div></div>'
        )

        html(
            '<hr style="border-color:rgba(255,255,255,0.08);margin:20px 0">'
            '<div style="font-size:0.6rem;color:#475569;text-align:center">'
            '&copy; 2025 INTAGE Healthcare Inc.</div>'
        )
        return consumers, personas


# ══════════════════════════════════════
# Header
# ══════════════════════════════════════


def header():
    html(
        f'<div style="background:linear-gradient(135deg,{NAVY},#132D4A);padding:28px 36px;'
        f'border-radius:16px;margin-bottom:24px;display:flex;align-items:center;'
        f'justify-content:space-between"><div>'
        f'<div style="font-size:1.8rem;font-weight:700;color:white;letter-spacing:-0.02em">'
        f'🌙 生活者AIペルソナ</div>'
        f'<div style="font-size:0.85rem;color:#94A3B8;margin-top:4px">'
        f'睡眠インタビューシミュレーター</div></div>'
        f'<div style="text-align:right">'
        f'<div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;'
        f'letter-spacing:0.1em;font-weight:600">Powered by</div>'
        f'<div style="font-size:0.95rem;color:white;font-weight:500">Claude API</div>'
        f'</div></div>'
    )


# ══════════════════════════════════════
# Tab 1: Persona Gallery
# ══════════════════════════════════════


def _persona_card(p: ConsumerPersona, c: Consumer):
    """ペルソナカードを表示する."""
    sp = c.sleep_profile
    concerns_text = "特になし"
    if sp and sp.concerns and sp.concerns != [SleepConcern.NONE]:
        concerns_text = "、".join(
            _CONCERN_JA.get(cc.value, cc.value) for cc in sp.concerns if cc != SleepConcern.NONE
        )

    products_text = "なし"
    if sp and sp.product_usage:
        products_text = "、".join(_PRODUCT_JA.get(pp.value, pp.value) for pp in sp.product_usage)

    quality = sp.sleep_quality_5 if sp else 3
    quality_bar = "●" * quality + "○" * (5 - quality)
    stress = sp.stress_level_5 if sp else 3
    stress_bar = "●" * stress + "○" * (5 - stress)
    sleep_h = f"{sp.avg_sleep_duration_hours:.1f}h" if sp else "?"

    demo = c.demographics
    with st.container(border=True):
        st.markdown(f"### {p.name}（{p.age}歳）")
        st.caption(p.catchphrase)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"**属性**: {_life_stage_ja(demo.life_stage.value)} / {demo.occupation or '未設定'}\n\n"
                f"**地域**: {_region_ja(demo.region.value)}\n\n"
                f"**年収**: {demo.household_income or '未設定'}"
            )
        with col2:
            st.markdown(
                f"**睡眠時間**: {sleep_h} / **満足度**: {quality_bar}\n\n"
                f"**ストレス**: {stress_bar}\n\n"
                f"**悩み**: {concerns_text}"
            )
        if products_text != "なし":
            st.markdown(f"**利用商品**: {products_text}")


def tab_gallery(personas: list[ConsumerPersona], consumers: list[Consumer]):
    st.subheader("ペルソナギャラリー")

    # フィルタ
    col1, col2, col3 = st.columns(3)
    with col1:
        age_filter = st.selectbox("年代", ["全て"] + [ag.value for ag in sorted(set(c.demographics.age_group for c in consumers))])
    with col2:
        gender_filter = st.selectbox("性別", ["全て", "male", "female"])
    with col3:
        concern_filter = st.selectbox("睡眠悩み", ["全て"] + [v for k, v in _CONCERN_JA.items() if k != "none"])

    # フィルタ適用
    filtered = list(zip(personas, consumers, strict=False))
    if age_filter != "全て":
        filtered = [(p, c) for p, c in filtered if c.demographics.age_group.value == age_filter]
    if gender_filter != "全て":
        filtered = [(p, c) for p, c in filtered if c.demographics.gender.value == gender_filter]
    if concern_filter != "全て":
        target_key = next((k for k, v in _CONCERN_JA.items() if v == concern_filter), None)
        if target_key:
            filtered = [
                (p, c) for p, c in filtered
                if c.sleep_profile and any(cc.value == target_key for cc in c.sleep_profile.concerns)
            ]

    st.caption(f"{len(filtered)} 件表示")

    # カード表示（3列）
    for i in range(0, min(len(filtered), 30), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(filtered):
                with col:
                    _persona_card(filtered[i + j][0], filtered[i + j][1])


# ══════════════════════════════════════
# Tab 2: Sleep Interview
# ══════════════════════════════════════


def tab_interview(personas: list[ConsumerPersona], consumers: list[Consumer]):
    st.subheader("🎤 睡眠インタビュー")

    # ペルソナ選択
    persona_options = {
        f"{p.name}（{p.age}歳・{_life_stage_ja(c.demographics.life_stage.value)}）": i
        for i, (p, c) in enumerate(zip(personas, consumers, strict=False))
        if c.sleep_profile and c.sleep_profile.concerns != [SleepConcern.NONE]
    }

    if not persona_options:
        st.warning("睡眠悩みのあるペルソナが見つかりません。")
        return

    selected_label = st.selectbox("インタビュー対象のペルソナを選択", list(persona_options.keys()))
    idx = persona_options[selected_label]
    persona = personas[idx]
    consumer = consumers[idx]

    # ペルソナ概要表示
    _persona_card(persona, consumer)

    st.divider()

    # 質問入力
    question = st.text_area(
        "質問を入力してください",
        value="寝つきが悪いときは、どんな工夫をしていますか？",
        height=80,
    )

    if st.button("🎤 インタビュー開始", type="primary", use_container_width=True):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。")
            return

        prompt = render_sleep_interview_prompt(
            consumer=consumer,
            persona_name=persona.name,
            age=persona.age,
            question=question,
        )

        with st.spinner(f"{persona.name} が回答を考えています..."):
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2048,
                    system=prompt.split("\n# Question\n")[0] if "\n# Question\n" in prompt else prompt,
                    messages=[{"role": "user", "content": question}],
                )
                answer = response.content[0].text

                st.markdown("---")
                st.markdown(f"**{persona.name}の回答:**")
                st.markdown(answer)

                # コスト・トークン情報
                usage = response.usage
                st.caption(
                    f"input: {usage.input_tokens} tokens / "
                    f"output: {usage.output_tokens} tokens / "
                    f"model: {response.model}"
                )

            except anthropic.APIError as e:
                st.error(f"Claude API エラー: {e}")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    # 過去のインタビューがセッションにあれば表示
    if "interview_history" not in st.session_state:
        st.session_state.interview_history = []


# ══════════════════════════════════════
# Tab 3: Sleep Distribution Analysis
# ══════════════════════════════════════


def tab_analysis(consumers: list[Consumer]):
    st.subheader("📊 睡眠データ分析")

    consumers_with_sleep = [c for c in consumers if c.sleep_profile is not None]
    if not consumers_with_sleep:
        st.warning("睡眠プロファイルのある生活者がいません。")
        return

    import plotly.graph_objects as go

    col1, col2 = st.columns(2)

    with col1:
        # 睡眠悩み分布
        concern_counts: dict[str, int] = {}
        for c in consumers_with_sleep:
            for cc in c.sleep_profile.concerns:
                if cc != SleepConcern.NONE:
                    label = _CONCERN_JA.get(cc.value, cc.value)
                    concern_counts[label] = concern_counts.get(label, 0) + 1

        if concern_counts:
            sorted_concerns = sorted(concern_counts.items(), key=lambda x: -x[1])
            fig = go.Figure(go.Bar(
                x=[v for _, v in sorted_concerns],
                y=[k for k, _ in sorted_concerns],
                orientation="h",
                marker_color=ACCENT,
            ))
            fig.update_layout(title="睡眠悩み分布", height=350, margin=dict(l=120, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 睡眠時間ヒストグラム
        durations = [c.sleep_profile.avg_sleep_duration_hours for c in consumers_with_sleep]
        fig = go.Figure(go.Histogram(x=durations, nbinsx=15, marker_color=GOLD))
        fig.update_layout(
            title="平均睡眠時間の分布",
            xaxis_title="時間",
            yaxis_title="人数",
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    # 年代×悩みクロス集計
    st.markdown("### 年代 × 睡眠悩み クロス集計")
    cross: dict[str, dict[str, int]] = {}
    for c in consumers_with_sleep:
        age = c.demographics.age_group.value
        for cc in c.sleep_profile.concerns:
            if cc != SleepConcern.NONE:
                label = _CONCERN_JA.get(cc.value, cc.value)
                cross.setdefault(age, {}).setdefault(label, 0)
                cross[age][label] += 1

    if cross:
        import pandas as pd

        df = pd.DataFrame(cross).T.fillna(0).astype(int)
        df.index.name = "年代"
        st.dataframe(df, use_container_width=True)


# ══════════════════════════════════════
# Main
# ══════════════════════════════════════


def main():
    result = sidebar()
    if result is None:
        return
    consumers, personas = result

    header()

    tabs = st.tabs(["🧑‍🤝‍🧑 ペルソナギャラリー", "🎤 睡眠インタビュー", "📊 データ分析"])

    with tabs[0]:
        tab_gallery(personas, consumers)

    with tabs[1]:
        tab_interview(personas, consumers)

    with tabs[2]:
        tab_analysis(consumers)


if __name__ == "__main__":
    main()
