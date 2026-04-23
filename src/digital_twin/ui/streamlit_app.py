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

from digital_twin.abm.consumer_agent import AdoptionState  # noqa: E402
from digital_twin.abm.data_bridge import consumers_to_agent_profiles  # noqa: E402
from digital_twin.abm.metrics import calculate_metrics  # noqa: E402
from digital_twin.abm.model import PrescriptionModel  # noqa: E402
from digital_twin.abm.visualization import plot_adoption_timeline, plot_network  # noqa: E402
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

    # フィルタ
    col1, col2, col3 = st.columns(3)
    with col1:
        iv_age_filter = st.selectbox(
            "年代",
            ["全て"] + [ag.value for ag in sorted(set(c.demographics.age_group for c in consumers))],
            key="iv_age",
        )
    with col2:
        iv_gender_filter = st.selectbox("性別", ["全て", "male", "female"], key="iv_gender")
    with col3:
        iv_concern_filter = st.selectbox(
            "睡眠悩み",
            ["全て"] + [v for k, v in _CONCERN_JA.items() if k != "none"],
            key="iv_concern",
        )

    # フィルタ適用
    pairs = [
        (p, c, i) for i, (p, c) in enumerate(zip(personas, consumers, strict=False))
        if c.sleep_profile and c.sleep_profile.concerns != [SleepConcern.NONE]
    ]
    if iv_age_filter != "全て":
        pairs = [(p, c, i) for p, c, i in pairs if c.demographics.age_group.value == iv_age_filter]
    if iv_gender_filter != "全て":
        pairs = [(p, c, i) for p, c, i in pairs if c.demographics.gender.value == iv_gender_filter]
    if iv_concern_filter != "全て":
        target_key = next((k for k, v in _CONCERN_JA.items() if v == iv_concern_filter), None)
        if target_key:
            pairs = [
                (p, c, i) for p, c, i in pairs
                if any(cc.value == target_key for cc in c.sleep_profile.concerns)
            ]

    # ペルソナ選択
    persona_options = {
        f"{p.name}（{p.age}歳・{_life_stage_ja(c.demographics.life_stage.value)}）": i
        for p, c, i in pairs
    }

    if not persona_options:
        st.warning("条件に合うペルソナが見つかりません。フィルタを変更してください。")
        return

    st.caption(f"{len(persona_options)} 件該当")
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
# Tab 3: Social Simulation (ABM)
# ══════════════════════════════════════

_STATE_LABELS_JA = {
    AdoptionState.NOT_ADOPTED: "未採用",
    AdoptionState.CONSIDERING: "検討中",
    AdoptionState.ADOPTED: "採用済み",
}


def tab_simulation(consumers: list[Consumer]):
    st.subheader("🔬 社会シミュレーション（ABM）")
    st.caption("生活者ネットワーク上での商品採用・口コミ伝播をシミュレーションします")

    # パラメータ設定
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_agents = st.slider("エージェント数", 30, 300, 100, step=10)
    with col2:
        kol_influence = st.slider("KOL 影響力", 0.05, 0.50, 0.15, step=0.05)
    with col3:
        peer_influence = st.slider("ピア影響力", 0.01, 0.20, 0.05, step=0.01)
    with col4:
        sim_steps = st.slider("シミュレーション期間（月）", 6, 48, 24, step=6)

    seed = st.number_input("乱数シード", value=42, step=1, min_value=0)

    if st.button("▶ シミュレーション実行", type="primary", use_container_width=True):
        with st.spinner("シミュレーション実行中..."):
            # Consumer データからエージェントプロファイルを生成
            profiles = consumers_to_agent_profiles(consumers[:n_agents])

            model = PrescriptionModel(
                agent_profiles=profiles,
                seed=int(seed),
                kol_influence=kol_influence,
                peer_influence=peer_influence,
            )

            history = model.run(steps=sim_steps)
            metrics = calculate_metrics(model.consumer_agents, history)

        # メトリクス表示
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("最終採用率", f"{metrics.final_adoption_rate:.1%}")
        m2.metric("平均採用期間", f"{metrics.mean_time_to_adoption:.1f} ヶ月")
        m3.metric("KOL 採用率", f"{metrics.influencer_adoption_rate:.1%}")
        m4.metric("一般 採用率", f"{metrics.non_influencer_adoption_rate:.1%}")

        # チャート
        col_left, col_right = st.columns(2)
        with col_left:
            st.plotly_chart(
                plot_adoption_timeline(history, title="採用率の時系列推移"),
                use_container_width=True,
            )
        with col_right:
            st.plotly_chart(
                plot_network(model.consumer_agents, model.network),
                use_container_width=True,
            )

        # カテゴリ別採用率
        if metrics.adoption_by_category:
            st.markdown("### カテゴリ別採用率")
            import pandas as pd

            cat_df = pd.DataFrame(
                [{"カテゴリ": k, "採用率": f"{v:.1%}"} for k, v in metrics.adoption_by_category.items()]
            )
            st.dataframe(cat_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════
# Main
# ══════════════════════════════════════


def main():
    result = sidebar()
    if result is None:
        return
    consumers, personas = result

    header()

    tabs = st.tabs(["🧑‍🤝‍🧑 ペルソナギャラリー", "🎤 睡眠インタビュー", "🔬 社会シミュレーション"])

    with tabs[0]:
        tab_gallery(personas, consumers)

    with tabs[1]:
        tab_interview(personas, consumers)

    with tabs[2]:
        tab_simulation(consumers)


if __name__ == "__main__":
    main()
