"""医師AIペルソナ — プロモーション反応シミュレーター."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parents[3]
load_dotenv(project_root / ".env")
sys.path.insert(0, str(project_root / "src"))

from digital_twin.data.anonymizer import anonymize_dataset  # noqa: E402
from digital_twin.data.loader import load_dataset, split_holdout  # noqa: E402
from digital_twin.persona.builder import PersonaBuilder  # noqa: E402
from digital_twin.persona.profile import (  # noqa: E402
    _channel_ja,
    _facility_ja,
    _region_ja,
    _rx_status_ja,
    _specialty_ja,
)

st.set_page_config(page_title="医師AIペルソナ", page_icon="🧬", layout="wide")

# ── Colors ──
NAVY = "#0B1929"
ACCENT = "#2E86AB"
GOLD = "#C4A35A"
GREEN = "#10B981"
WARN = "#F59E0B"
RED = "#EF4444"
GRAY = "#64748B"
ADOPT_C = {"early": GREEN, "moderate": ACCENT, "late": WARN}
ADOPT_L = {"early": "早期採用", "moderate": "標準", "late": "慎重派"}
INTENT_L = {"start": "新規採用", "increase": "増やしたい", "maintain": "現状維持", "decrease": "減らしたい", "no_intent": "処方予定なし"}
INTENT_C = {"start": GREEN, "increase": "#059669", "maintain": ACCENT, "decrease": WARN, "no_intent": RED}


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


# ── Global CSS (only overriding Streamlit internals, no custom classes) ──
html("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter','Noto Sans JP',sans-serif; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg,#0B1929,#132D4A); }
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
#MainMenu, footer { visibility: hidden; }
.stTabs [data-baseweb="tab-list"] { background: #fff; border-radius: 12px; padding: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.stTabs [aria-selected="true"] { background: #0B1929 !important; color: white !important; border-radius: 10px; }
</style>""")


@st.cache_data
def load_data(data_dir: str):
    physicians, surveys, scenarios = load_dataset(data_dir)
    safe, report = anonymize_dataset(physicians, k=3)
    train, holdout = split_holdout(safe, holdout_ratio=0.3)
    builder = PersonaBuilder(max_historical=8)
    sid = surveys[0].survey_id if surveys else None
    personas = builder.build_batch(train, surveys, training_survey_ids=[sid] if sid else None)
    return dict(physicians=safe, train=train, holdout=holdout, surveys=surveys,
                scenarios=scenarios, personas=personas, report=report)


# ══════════════════════════════════════
# Sidebar
# ══════════════════════════════════════
def sidebar():
    with st.sidebar:
        html(f'<div style="text-align:center;padding:20px 0 10px"><div style="font-size:1.5rem;font-weight:700;color:white">医師AIペルソナ</div><div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;letter-spacing:0.1em;margin-top:4px">Promotion Response Simulator</div></div><hr style="border-color:rgba(255,255,255,0.08);margin:12px 0 20px">')
        data_dir = st.text_input("Data Source", value="./data/dummy", label_visibility="collapsed")
        if not (Path(data_dir) / "physicians.json").exists():
            st.error("データが見つかりません。以下を実行してください: python scripts/generate_dummy_data.py")
            return None
        data = load_data(data_dir)
        n = len(data["physicians"])
        np_ = len(data["personas"])
        ns = len(data["scenarios"])
        html(f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:16px 0"><div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center"><div style="font-size:1.4rem;font-weight:700;color:white">{n}</div><div style="font-size:0.65rem;color:#94A3B8">医師数</div></div><div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center"><div style="font-size:1.4rem;font-weight:700;color:{GOLD}">{np_}</div><div style="font-size:0.65rem;color:#94A3B8">ペルソナ数</div></div><div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center"><div style="font-size:1.4rem;font-weight:700;color:white">{ns}</div><div style="font-size:0.65rem;color:#94A3B8">シナリオ数</div></div><div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:12px;text-align:center"><div style="font-size:1.4rem;font-weight:700;color:white">{len(data["surveys"])}</div><div style="font-size:0.65rem;color:#94A3B8">調査数</div></div></div>')
        html('<hr style="border-color:rgba(255,255,255,0.08);margin:20px 0"><div style="font-size:0.6rem;color:#475569;text-align:center">&copy; 2025 INTAGE Healthcare Inc.</div>')
        return data


# ══════════════════════════════════════
# Header
# ══════════════════════════════════════
def header():
    html(f'<div style="background:linear-gradient(135deg,{NAVY},#132D4A);padding:28px 36px;border-radius:16px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between"><div><div style="font-size:1.8rem;font-weight:700;color:white;letter-spacing:-0.02em">医師AIペルソナ</div><div style="font-size:0.85rem;color:#94A3B8;margin-top:4px">プロモーション反応シミュレーター &mdash; 処方意向予測</div></div><div style="text-align:right"><div style="font-size:0.65rem;color:{GOLD};text-transform:uppercase;letter-spacing:0.1em;font-weight:600">Powered by</div><div style="font-size:0.95rem;color:white;font-weight:500">INTAGE Healthcare</div></div></div>')


# ══════════════════════════════════════
# Tab 1: Persona Gallery
# ══════════════════════════════════════
def tab_persona_gallery(personas):
    c1, c2, c3 = st.columns(3)
    specs = sorted(set(_specialty_ja(p.demographics.specialty.value) for p in personas))
    facs = sorted(set(_facility_ja(p.demographics.facility_type.value) for p in personas))
    with c1:
        sf = st.selectbox("診療科", ["すべて"] + specs)
    with c2:
        ff = st.selectbox("施設タイプ", ["すべて"] + facs)
    with c3:
        af = st.selectbox("新薬採用速度", ["すべて", "早期採用", "標準", "慎重派"])

    filtered = personas
    if sf != "すべて":
        filtered = [p for p in filtered if _specialty_ja(p.demographics.specialty.value) == sf]
    if ff != "すべて":
        filtered = [p for p in filtered if _facility_ja(p.demographics.facility_type.value) == ff]
    if af != "すべて":
        am = {"早期採用": "early", "標準": "moderate", "慎重派": "late"}
        filtered = [p for p in filtered if p.prescription_profile.new_drug_adoption_speed == am.get(af)]

    st.caption(f"{len(filtered)} 件のペルソナ")

    for i in range(0, min(len(filtered), 12), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(filtered):
                with col:
                    persona_card(filtered[i + j])


def persona_card(p):
    demo = p.demographics
    rx = p.prescription_profile
    speed = rx.new_drug_adoption_speed
    color = ADOPT_C.get(speed, GRAY)
    label = ADOPT_L.get(speed, speed)
    spec = _specialty_ja(demo.specialty.value)
    fac = _facility_ja(demo.facility_type.value)
    region = _region_ja(demo.region.value)
    kol = ' <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.65rem;font-weight:600;background:#FDE68A;color:#78350F">KOL</span>' if demo.is_key_opinion_leader else ""

    channels = sorted(p.channel_preferences, key=lambda c: -c.receptivity)[:3]
    ch_html = " ".join(f'<span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.65rem;background:#F1F5F9;color:#475569;border:1px solid #E2E8F0;margin:2px">{_channel_ja(c.channel.value)}</span>' for c in channels)

    facts = "".join(f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;padding:6px 12px;margin:3px 0;font-size:0.78rem;line-height:1.5">{f.content}</div>' for f in p.factoids[:2])

    drugs_primary = ", ".join(rx.primary_drugs[:3])
    philosophy = rx.prescribing_philosophy[:50]

    html(f"""<div style="background:#fff;border:1px solid #E2E8F0;border-radius:16px;padding:24px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.04)">
<div style="display:flex;justify-content:space-between;align-items:flex-start">
<div><div style="font-size:1.1rem;font-weight:600;color:{NAVY}">{p.name}</div>
<div style="font-size:0.78rem;color:{GRAY}">{p.age}歳 · {spec} · {fac}（{region}）</div></div>
<div><span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:0.68rem;font-weight:600;background:{color}22;color:{color}">{label}</span>{kol}</div></div>
<div style="font-size:0.83rem;font-style:italic;color:#132D4A;background:#E8F4F8;border-left:3px solid {ACCENT};padding:8px 14px;border-radius:0 8px 8px 0;margin:12px 0">{p.catchphrase}</div>
<div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:{GRAY};margin:14px 0 6px;padding-bottom:4px;border-bottom:1px solid #F1F5F9">処方プロファイル</div>
<div style="font-size:0.8rem;line-height:1.7">主要処方薬: <b>{drugs_primary}</b><br>処方哲学: {philosophy}...</div>
<div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:{GRAY};margin:14px 0 6px;padding-bottom:4px;border-bottom:1px solid #F1F5F9">情報チャネル</div>
{ch_html}
<div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:{GRAY};margin:14px 0 6px;padding-bottom:4px;border-bottom:1px solid #F1F5F9">主なファクトイド</div>
{facts}
</div>""")

    with st.expander(f"詳細 — {p.name}"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**ゴール**")
            for g in p.goals:
                st.write(f"{'★' * (6 - g.priority)} {g.description}")
            st.markdown("**薬剤別処方状況**")
            for drug, status in rx.drug_prescription_status.items():
                st.write(f"● {drug}: {_rx_status_ja(status.value)}")
        with c2:
            fig = radar_chart(p)
            st.plotly_chart(fig, config={"displayModeBar": False})


def radar_chart(p):
    prefs = sorted(p.channel_preferences, key=lambda x: x.channel.value)
    cats = [_channel_ja(c.channel.value) for c in prefs]
    vals = [c.receptivity for c in prefs]
    cats.append(cats[0])
    vals.append(vals[0])
    fig = go.Figure(go.Scatterpolar(r=vals, theta=cats, fill="toself",
                                     fillcolor="rgba(46,134,171,0.15)", line=dict(color=ACCENT, width=2)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5], showticklabels=False)),
                       showlegend=False, height=260, margin=dict(l=40, r=40, t=20, b=20),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ══════════════════════════════════════
# Tab 2: Promotion Simulator
# ══════════════════════════════════════
def tab_promotion_sim(personas, scenarios):
    mode = st.radio("入力方法", ["シナリオ選択", "自由入力"], horizontal=True, label_visibility="collapsed")

    left, right = st.columns([3, 2])

    with left:
        if mode == "シナリオ選択" and scenarios:
            names = {f"{s.product_name} — {_channel_ja(s.channel.value)}": s for s in scenarios}
            sel = st.selectbox("シナリオ", list(names.keys()), label_visibility="collapsed")
            base = names[sel]
            msg = st.text_area("キーメッセージ", value=base.key_message, height=100)
            clin = st.text_area("臨床エビデンス", value=base.clinical_data_summary or "", height=80)
            from digital_twin.data.schema import PromotionScenario
            scenario = PromotionScenario(scenario_id=base.scenario_id, pharma_company=base.pharma_company,
                product_name=base.product_name, therapeutic_area=base.therapeutic_area,
                channel=base.channel, key_message=msg, detail_content=base.detail_content,
                clinical_data_summary=clin, is_new_drug=base.is_new_drug)
        else:
            c1, c2 = st.columns(2)
            with c1:
                pharma = st.text_input("製薬企業", value="")
                product = st.text_input("製品名", value="")
            with c2:
                area = st.text_input("疾患領域", value="乳がん")
                from digital_twin.data.schema import PromotionChannel
                ch_opts = {_channel_ja(ch.value): ch for ch in PromotionChannel}
                sel_ch = st.selectbox("チャネル", list(ch_opts.keys()))
            is_new = st.toggle("新薬", value=True)
            msg = st.text_area("キーメッセージ", value="", height=120, placeholder="プロモーションのキーメッセージを入力...")
            detail = st.text_area("ディテール内容（任意）", value="", height=60)
            clin = st.text_area("臨床エビデンス（任意）", value="", height=60)
            from digital_twin.data.schema import PromotionScenario
            scenario = PromotionScenario(scenario_id="CUSTOM", pharma_company=pharma, product_name=product,
                therapeutic_area=area, channel=ch_opts[sel_ch], key_message=msg,
                detail_content=detail, clinical_data_summary=clin, is_new_drug=is_new)

    with right:
        n = st.slider("対象医師数", 1, min(20, len(personas)), 5)
        section_header("対象パネル")
        for p in personas[:n]:
            sp = p.prescription_profile.new_drug_adoption_speed
            st.write(f"● {p.name} — {_specialty_ja(p.demographics.specialty.value)} ({ADOPT_L[sp]})")

    if not scenario.key_message.strip():
        st.info("キーメッセージを入力してください。")
        return

    if st.button("シミュレーション実行", type="primary"):
        if not scenario.product_name:
            st.warning("製品名を入力してください。")
            return
        run_simulation(personas[:n], scenario)


def run_simulation(personas, scenario):
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY が設定されていません。`.env` ファイルまたは環境変数で設定してください。")
        return
    try:
        from digital_twin.engine.simulator import Simulator
        sim = Simulator(model="claude-sonnet-4-20250514", temperature=0.8, max_concurrent=5)
        results = []
        bar = st.progress(0, text="準備中...")
        for i, p in enumerate(personas):
            bar.progress((i + 1) / len(personas), text=f"{p.name} をシミュレーション中...")
            results.append(sim.simulate_promotion(p, scenario))
        bar.progress(1.0, text="完了")

        intents = [r.responses.get("prescription_intent", "") for r in results]
        evals = [r.responses.get("message_evaluation", 0) for r in results]
        fits = [r.responses.get("channel_fit", 0) for r in results]
        pos = sum(1 for i in intents if i in ("start", "increase"))
        pos_pct = pos / len(intents) * 100 if intents else 0
        avg_eval = sum(evals) / len(evals) if evals else 0
        avg_fit = sum(fits) / len(fits) if fits else 0

        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("処方意向ポジティブ率", f"{pos_pct:.0f}%")
        k2.metric("メッセージ評価（平均）", f"{avg_eval:+.1f}")
        k3.metric("チャネル適合度", f"{avg_fit:.1f}/5")
        k4.metric("回答数", len(results))

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            ic = Counter(intents)
            fig = go.Figure(go.Pie(labels=[INTENT_L.get(k, k) for k in ic], values=list(ic.values()),
                                    marker=dict(colors=[INTENT_C.get(k, GRAY) for k in ic]), hole=0.55))
            fig.update_layout(title="処方意向分布", height=320, showlegend=True,
                               margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, config={"displayModeBar": False})
        with c2:
            ec = Counter(evals)
            el = {2: "+2 喜ぶ", 1: "+1 役立つ", 0: "0 無関心", -1: "-1 困惑"}
            ecol = {2: GREEN, 1: ACCENT, 0: GRAY, -1: RED}
            se = sorted(ec.keys())
            fig = go.Figure(go.Bar(y=[el.get(k, str(k)) for k in se], x=[ec[k] for k in se],
                                    orientation="h", marker_color=[ecol.get(k, GRAY) for k in se]))
            fig.update_layout(title="メッセージ評価分布", height=320, margin=dict(l=20, r=20, t=50, b=20))
            st.plotly_chart(fig, config={"displayModeBar": False})

        # Individual results
        section_header("医師別 個別回答")
        for r in results:
            resp = r.responses
            ik = resp.get("prescription_intent", "")
            il = INTENT_L.get(ik, ik)
            ic_ = INTENT_C.get(ik, GRAY)
            ev = resp.get("message_evaluation", 0)
            cf = resp.get("channel_fit", 0)

            html(f"""<div style="background:#fff;border:1px solid #E2E8F0;border-radius:14px;overflow:hidden;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.04)">
<div style="padding:16px 24px;border-bottom:1px solid #F1F5F9;background:linear-gradient(90deg,{ic_}15,transparent)">
<b style="font-size:0.95rem">{r.persona_name}</b>
<span style="margin-left:12px;font-size:0.8rem">処方意向: <b style="color:{ic_}">{il}</b> · 評価: <b>{ev:+d}</b> · 適合度: {'★' * cf}{'☆' * (5 - cf)}</span>
</div>
<div style="padding:20px 24px">
<div style="font-size:0.85rem;line-height:1.7;margin-bottom:10px">{resp.get('intent_reason', '')}</div>
<div style="background:#F8FAFC;border-radius:10px;padding:14px 18px;font-size:0.83rem;line-height:1.7;margin-bottom:10px">{resp.get('message_feedback', '')}</div>
<div style="font-size:0.8rem"><b>追加情報ニーズ:</b> {resp.get('information_needs', '')}</div>
<div style="font-size:0.8rem;font-style:italic;color:{GRAY};margin-top:6px">{resp.get('walkthrough', '')}</div>
</div></div>""")

        # Export
        export = [{"persona": r.persona_name, "persona_id": r.persona_id, **r.responses} for r in results]
        e1, e2 = st.columns(2)
        with e1:
            st.download_button("CSV ダウンロード", pd.DataFrame(export).to_csv(index=False).encode("utf-8-sig"),
                               "results.csv", "text/csv")
        with e2:
            st.download_button("JSON ダウンロード", json.dumps(export, ensure_ascii=False, indent=2),
                               "results.json", "application/json")

        cost = sim.get_cost_summary()
        st.caption(f"API呼び出し: {cost['total_calls']}回 | コスト: ${cost['total_cost_usd']:.4f}")
    except Exception as e:
        st.error(f"エラー: {e}")


# ══════════════════════════════════════
# Tab 3: Panel Analytics
# ══════════════════════════════════════
def tab_analytics(data):
    for survey in data["surveys"]:
        section_header(survey.survey_name)
        qs = [q for q in survey.questions if q.options]
        for i in range(0, len(qs), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j >= len(qs):
                    break
                q = qs[i + j]
                resps = []
                for doc in data["physicians"]:
                    for sr in doc.survey_responses:
                        if sr.survey_id != survey.survey_id:
                            continue
                        for qr in sr.responses:
                            if qr.question_id == q.question_id and qr.response_value:
                                v = qr.response_value
                                if isinstance(v, list):
                                    resps.extend(str(x) for x in v)
                                else:
                                    resps.append(str(v))
                if resps:
                    ct = Counter(resps)
                    tot = sum(ct.values())
                    fig = go.Figure(go.Bar(x=list(ct.keys()), y=[v / tot * 100 for v in ct.values()],
                                           marker_color=ACCENT))
                    fig.update_layout(title=f"{q.question_id}: {q.question_text[:50]}", height=300,
                                      yaxis_title="%", margin=dict(l=20, r=20, t=50, b=20))
                    with col:
                        st.plotly_chart(fig, config={"displayModeBar": False})


# ══════════════════════════════════════
# Tab 4: Skill.md Export
# ══════════════════════════════════════
def tab_skill(personas):
    if not personas:
        return
    left, right = st.columns([1, 2])
    with left:
        section_header("ペルソナ選択")
        pmap = {f"{p.name} — {_specialty_ja(p.demographics.specialty.value)}": p for p in personas}
        sel = st.radio("Persona", list(pmap.keys()), label_visibility="collapsed")
        p = pmap[sel]
        st.write(f"**{p.name}** ({p.age}歳)")
        st.write(f"_{p.catchphrase}_")
        md = p.to_skill_md()
        st.download_button("Skill.md ダウンロード", md, f"skill_{p.persona_id}.md", "text/markdown")
    with right:
        section_header("システムプロンプト プレビュー")
        st.code(p.to_system_prompt(), language="markdown")


# ══════════════════════════════════════
# Tab 5: Validation
# ══════════════════════════════════════
def tab_validation(data):
    r = data["report"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("医師数", r.total_physicians)
    c2.metric("属性グループ数", r.demographic_groups)
    c3.metric("k-匿名性", f"k={r.k_anonymity_achieved}")
    c4.metric("抑制件数", r.suppressed_physicians)

    docs = data["physicians"]
    c1, c2 = st.columns(2)
    with c1:
        sp = Counter(_specialty_ja(p.demographics.specialty.value) for p in docs)
        fig = go.Figure(go.Pie(labels=list(sp.keys()), values=list(sp.values()), hole=0.5))
        fig.update_layout(title="診療科分布", height=320, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, config={"displayModeBar": False})
    with c2:
        fc = Counter(_facility_ja(p.demographics.facility_type.value) for p in docs)
        fig = go.Figure(go.Bar(x=list(fc.keys()), y=list(fc.values()), marker_color=ACCENT))
        fig.update_layout(title="施設タイプ分布", height=320, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, config={"displayModeBar": False})

    section_header("PoC 判定基準")

    # バリデーション用サーベイ選択
    surveys = data.get("surveys", [])
    if not surveys:
        st.warning("サーベイデータがありません。")
        return

    survey_names = {s.survey_name: s for s in surveys}
    sel_survey = st.selectbox("検証用サーベイ", list(survey_names.keys()))
    survey = survey_names[sel_survey]

    if st.button("バリデーション実行", type="primary"):
        _run_validation(data, survey)
    else:
        st.info("「バリデーション実行」をクリックすると、ホールドアウトデータに対する検証を行います。")


def _run_validation(data, survey):
    """ホールドアウトデータに対してバリデーションを実行し、結果を表示する。"""
    import os

    from digital_twin.engine.simulator import Simulator
    from digital_twin.evaluation.validator import validate
    from digital_twin.persona.builder import PersonaBuilder as _Builder

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("ANTHROPIC_API_KEY が設定されていません。")
        return

    holdout = data["holdout"]
    surveys = data["surveys"]

    if not holdout:
        st.warning("ホールドアウトデータがありません。")
        return

    # ホールドアウト医師からペルソナを構築（train のペルソナとは別）
    builder = _Builder(max_historical=8, seed=42)
    holdout_personas = builder.build_batch(holdout, surveys)

    if not holdout_personas:
        st.warning("ホールドアウトに対応するペルソナを構築できませんでした。")
        return

    # シミュレーション実行
    sim = Simulator(model="claude-sonnet-4-20250514", temperature=0.8)
    bar = st.progress(0, text="シミュレーション中...")
    sim_results = []
    for i, p in enumerate(holdout_personas):
        bar.progress((i + 1) / len(holdout_personas), text=f"{p.name} を検証中...")
        sim_results.append(sim.simulate_survey(p, survey))
    bar.progress(1.0, text="検証完了")

    # バリデーション実行
    report = validate(
        real_respondents=holdout,
        simulation_results=sim_results,
        validation_survey_id=survey.survey_id,
    )

    # 全体判定
    overall_color = GREEN if report.overall_pass else RED
    overall_label = "PASS" if report.overall_pass else "FAIL"
    html(f'<div style="background:{overall_color}15;border:2px solid {overall_color};border-radius:12px;padding:16px 24px;margin:16px 0;text-align:center"><span style="font-size:1.4rem;font-weight:700;color:{overall_color}">{overall_label}</span><span style="font-size:0.9rem;color:{GRAY};margin-left:12px">Pass Rate: {report.pass_rate:.0%} ({report.n_questions} questions, {report.n_respondents} respondents)</span></div>')

    # メトリクス詳細テーブル
    rows = []
    for m in report.metrics:
        status_label = "PASS" if m.passed else "FAIL"
        rows.append({
            "指標": m.name,
            "値": f"{m.value:.4f}",
            "閾値": f"{m.threshold:.4f}",
            "判定": status_label,
            "詳細": m.details,
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, column_config={
            "判定": st.column_config.TextColumn(width="small"),
        })
    else:
        st.warning("評価対象の設問が見つかりませんでした。")

    # コスト表示
    cost = sim.get_cost_summary()
    st.caption(f"API呼び出し: {cost['total_calls']}回 | コスト: ${cost['total_cost_usd']:.4f}")


# ══════════════════════════════════════
# Evidence Traceability (根拠トレーサビリティ)
# ══════════════════════════════════════
def _show_evidence_panel(result):
    """回答のデータソース出典を視覚表示する."""
    if not result.evidence_sources:
        return

    # ソース構成サマリー
    from collections import Counter as _Counter
    source_counts = _Counter(result.evidence_sources)
    source_colors = {
        "impact_track": ACCENT, "soc": GOLD, "repi": GREEN,
        "logscape": "#8B5CF6", "cross_analysis": "#EC4899",
    }

    html('<div style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0">'
         + "".join(
             f'<span style="display:inline-block;padding:3px 10px;border-radius:16px;font-size:0.7rem;'
             f'font-weight:600;background:{source_colors.get(src, GRAY)}22;'
             f'color:{source_colors.get(src, GRAY)}">{src}: {cnt}件</span>'
             for src, cnt in source_counts.most_common()
         )
         + '</div>')

    with st.expander(f"参照データソース詳細（{len(result.evidence_sources)}件）"):
        for i, src in enumerate(result.evidence_sources):
            st.markdown(f"**{i + 1}.** `{src}`")


# ══════════════════════════════════════
# Helpers
# ══════════════════════════════════════
def section_header(text):
    html(f'<div style="font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:{GRAY};margin:18px 0 8px;padding-bottom:6px;border-bottom:1px solid #F1F5F9">{text}</div>')


# ══════════════════════════════════════
# Main
# ══════════════════════════════════════
def tab_dialogue(personas, key_prefix: str = "dlg"):
    """対話型シミュレーションタブ（RAG対応）."""
    section_header("セグメント選択")
    c1, c2, c3 = st.columns(3)
    with c1:
        specialty = st.selectbox("診療科", ["腫瘍内科", "乳腺外科", "外科"], key=f"{key_prefix}_spec")
    with c2:
        bed_size = st.selectbox("病床数", ["500床以上", "200-499床", "20床未満"], key=f"{key_prefix}_bed")
    with c3:
        age_range = st.selectbox("年代", ["40代", "50代", "60代"], key=f"{key_prefix}_age")

    section_header("ペルソナ選択")
    pmap = {f"{p.name} — {_specialty_ja(p.demographics.specialty.value)}": p for p in personas[:10]}
    sel = st.selectbox("ペルソナ", list(pmap.keys()), key=f"{key_prefix}_persona")
    persona = pmap[sel]

    section_header("質問入力")
    query = st.text_area("質問を入力してください", height=100, key=f"{key_prefix}_query",
                         placeholder="例: この薬剤のエビデンスについてどう思いますか？")

    if st.button("対話実行", type="primary", key=f"{key_prefix}_run"):
        if not query.strip():
            st.warning("質問を入力してください。")
            return

        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY が設定されていません。`.env` ファイルまたは環境変数で設定してください。")
            return

        segment = {"specialty": specialty, "bed_size": bed_size, "age_range": age_range}

        with st.spinner(f"{persona.name} が回答中..."):
            try:
                from digital_twin.engine.simulator import Simulator
                sim = Simulator(model="claude-sonnet-4-20250514", temperature=0.8)
                result = sim.simulate_dialogue(persona, query, segment=segment)

                # 確信度ラベル表示
                if result.confidence_level:
                    conf_color = {"[データ根拠あり]": GREEN, "[推論]": WARN, "[データ外]": RED}
                    color = conf_color.get(result.confidence_level, GRAY)
                    html(f'<span style="display:inline-block;padding:4px 12px;border-radius:12px;'
                         f'font-size:0.75rem;font-weight:600;background:{color}22;color:{color}">'
                         f'{result.confidence_level}</span>')

                # 回答表示
                st.markdown(f"**{persona.name}の回答:**")
                st.markdown(result.response_text)

                # 根拠トレーサビリティ表示
                _show_evidence_panel(result)

                # コスト
                st.caption(f"Tokens: {result.input_tokens} in / {result.output_tokens} out")
            except Exception as e:
                st.error(f"エラー: {e}")
    else:
        st.info("質問を入力して「対話実行」をクリックしてください。")


def tab_integrated_demo(data):
    """統合デモ — 対話→プレテスト→シミュレーションの3ステップフロー."""
    step = st.radio("ステップ", ["Step 1: 対話", "Step 2: プレテスト", "Step 3: 社会シミュレーション"], horizontal=True)

    if step == "Step 1: 対話":
        section_header("Step 1: 対話型シミュレーション")
        st.info("セグメントを選択し、ペルソナと対話して施策の感触を掴みます。")
        tab_dialogue(data["personas"], key_prefix="demo_dlg")

    elif step == "Step 2: プレテスト":
        section_header("Step 2: 施策プレテスト")
        st.info("施策シナリオを定義し、処方ポテンシャルへの影響を定量評価します。")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**施策シナリオ定義**")
            scenario_name = st.text_input("シナリオ名", value="MRディテール+2回", key="demo_scenario")
            features = {
                "dtl_mr_positive": st.slider("MRディテール（ポジティブ）", 0.0, 5.0, 2.0, key="demo_mr"),
                "dtl_web_positive": st.slider("Web講演会（ポジティブ）", 0.0, 5.0, 0.0, key="demo_web"),
                "repi_score": st.slider("MR評価スコア", 0.0, 5.0, 0.0, key="demo_repi"),
            }

        with c2:
            st.markdown("**予測結果**")
            if st.button("プレテスト実行", type="primary", key="demo_pretest"):
                try:
                    from digital_twin.pretest.potential_model import PotentialModel
                    from digital_twin.pretest.scenario_engine import PretestScenario, ScenarioEngine

                    model_path = Path("tests/fixtures/dummy_potential_model.joblib")
                    if model_path.exists():
                        model = PotentialModel.load(model_path)
                        engine = ScenarioEngine(model)
                        scenario = PretestScenario(
                            scenario_name=scenario_name,
                            delta_features={k: v for k, v in features.items() if v > 0},
                        )
                        result = engine.calculate_delta(scenario)
                        st.metric("スコア変化", f"{result.delta:+.4f}", delta=f"{result.delta:+.4f}")
                        st.metric("ベース → シナリオ後", f"{result.base_score:.4f} → {result.new_score:.4f}")

                        st.markdown("**特徴量寄与度**")
                        for feat, contrib in sorted(result.feature_contributions.items(), key=lambda x: -abs(x[1])):
                            if contrib != 0:
                                st.write(f"- {feat}: {contrib:+.4f}")
                    else:
                        st.warning("ダミーモデルが見つかりません。tests/fixtures/create_dummy_model.py を実行してください。")
                except Exception as e:
                    st.error(f"エラー: {e}")

    elif step == "Step 3: 社会シミュレーション":
        section_header("Step 3: 社会シミュレーション（ABM）")
        st.info("採用の波及効果をエージェントベースモデルで予測します。")

        abm_mode = st.radio("モード", ["シナリオ実行", "感度分析"], horizontal=True, key="abm_mode")

        if abm_mode == "シナリオ実行":
            _abm_scenario_run(data)
        else:
            _abm_sensitivity_analysis()


def _abm_scenario_run(data):
    """シナリオ選択 → シミュレーション実行."""
    from digital_twin.abm.scenarios import load_scenarios

    scenarios = load_scenarios()
    names = [s.name for s in scenarios]

    c1, c2 = st.columns([1, 2])
    with c1:
        sel_name = st.selectbox("シナリオ", names, key="abm_scenario")
        scenario = next(s for s in scenarios if s.name == sel_name)

        st.markdown(f"**薬剤**: {scenario.product or '（カスタム）'}")
        st.markdown(f"**疾患領域**: {scenario.therapeutic_area or '—'}")
        st.markdown(f"**期間**: {scenario.duration_steps} {scenario.step_unit}")
        st.markdown(f"**イベント数**: {len(scenario.events)}")

        # データソース選択
        data_source = st.radio("エージェント生成", ["実データから", "手動設定"], key="abm_data_src")

        if data_source == "手動設定":
            n_agents = st.slider("エージェント数", 10, 200, 50, key="abm_n")
        else:
            n_agents = min(len(data.get("physicians", [])), 200)
            st.caption(f"医師データ: {n_agents}名")

        st.selectbox("伝播モデル", ["線形閾値", "独立カスケード"], key="abm_prop")

    with c2:
        if st.button("シミュレーション実行", type="primary", key="abm_run"):
            try:
                from digital_twin.abm.data_bridge import physicians_to_agent_profiles
                from digital_twin.abm.events import EventScheduler
                from digital_twin.abm.metrics import calculate_metrics
                from digital_twin.abm.model import PrescriptionModel
                from digital_twin.abm.physician_agent import AdoptionState, AgentProfile
                from digital_twin.abm.visualization import plot_adoption_timeline

                # エージェント生成
                if data_source == "実データから" and data.get("physicians"):
                    profiles = physicians_to_agent_profiles(data["physicians"][:n_agents])
                else:
                    profiles = [
                        AgentProfile(
                            specialty=spec,
                            kol_score=0.9 if i < scenario.initial_adopters.get("kol", 3) else 0.2,
                            adoption_threshold=0.2 if i < scenario.initial_adopters.get("kol", 3) else 0.5,
                        )
                        for i, spec in enumerate(
                            scenario.target_specialties * (n_agents // max(len(scenario.target_specialties), 1) + 1)
                        )
                    ][:n_agents]

                model = PrescriptionModel(profiles, seed=42)

                # 初期採用者設定
                n_kol = scenario.initial_adopters.get("kol", 3)
                n_early = scenario.initial_adopters.get("early_adopter", 5)
                for i in range(min(n_kol + n_early, len(model.physician_agents))):
                    model.physician_agents[i].state = AdoptionState.ADOPTED
                    model.physician_agents[i].adoption_step = 0

                # イベントスケジューラ
                scheduler = EventScheduler()
                for evt in scenario.events:
                    scheduler.add_event(evt)

                # シミュレーション実行（イベント付き）
                history = []
                for s in range(scenario.duration_steps):
                    scheduler.apply_events(s + 1, model.physician_agents)
                    model.step()
                    history.append({
                        "step": model._steps,
                        **model.get_adoption_count(),
                        "adoption_rate": model.get_adoption_rate(),
                    })

                # チャート
                event_markers = [{"step": e.start_step, "name": e.name} for e in scenario.events]
                fig = plot_adoption_timeline(history, event_steps=event_markers,
                                            title=f"採用率推移 — {scenario.name}")
                fig.update_xaxes(title_text=f"タイムステップ（{scenario.step_unit}）")
                st.plotly_chart(fig, config={"displayModeBar": False})

                # メトリクス
                metrics = calculate_metrics(model.physician_agents, history)
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("最終採用率", f"{metrics.final_adoption_rate:.0%}")
                k2.metric("採用済み", metrics.total_adopted)
                k3.metric("平均採用時間", f"{metrics.mean_time_to_adoption:.1f} {scenario.step_unit}")
                k4.metric("KOL採用率", f"{metrics.kol_adoption_rate:.0%}")

                # 診療科別
                if metrics.adoption_by_specialty:
                    with st.expander("診療科別採用率"):
                        for spec, rate in sorted(metrics.adoption_by_specialty.items(), key=lambda x: -x[1]):
                            st.write(f"- {spec}: {rate:.0%}")

            except Exception as e:
                st.error(f"エラー: {e}")


def _abm_sensitivity_analysis():
    """パラメータ感度分析 UI."""
    from digital_twin.abm.calibration import sensitivity_analysis
    from digital_twin.abm.physician_agent import AgentProfile

    section_header("パラメータ感度分析")
    st.info("パラメータを変化させた時の採用率推移を比較します。")

    c1, c2 = st.columns([1, 2])
    with c1:
        param = st.selectbox("分析パラメータ", ["kol_influence", "peer_influence"], key="sa_param")
        n_agents = st.slider("エージェント数", 10, 100, 30, key="sa_n")
        n_steps = st.slider("ステップ数", 10, 50, 20, key="sa_steps")

        values = (
            [0.05, 0.10, 0.15, 0.20, 0.30, 0.40] if param == "kol_influence"
            else [0.01, 0.03, 0.05, 0.08, 0.10, 0.15]
        )

    with c2:
        if st.button("感度分析実行", type="primary", key="sa_run"):
            profiles = [
                AgentProfile(specialty="oncology", kol_score=0.9 if i < 3 else 0.2, adoption_threshold=0.3)
                for i in range(n_agents)
            ]

            results = sensitivity_analysis(profiles, param, values, steps=n_steps)

            import plotly.graph_objects as go_fig
            fig = go_fig.Figure()
            for r in results:
                fig.add_trace(go_fig.Scatter(
                    x=list(range(1, len(r["curve"]) + 1)),
                    y=r["curve"],
                    mode="lines",
                    name=f"{param}={r['param_value']}",
                ))
            fig.update_layout(
                title=f"感度分析: {param}",
                xaxis_title="タイムステップ",
                yaxis_title="採用率",
                yaxis={"range": [0, 1]},
                height=400,
            )
            st.plotly_chart(fig, config={"displayModeBar": False})

            st.markdown("**最終採用率の比較**")
            for r in results:
                st.write(f"- {param}={r['param_value']}: **{r['final_adoption_rate']:.0%}**")


def main():
    data = sidebar()
    if data is None:
        return
    header()
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "ペルソナ一覧", "プロモーション シミュレーション", "パネル分析",
        "Skill.md エクスポート", "検証", "対話シミュレーション", "統合デモ",
    ])
    with t1:
        tab_persona_gallery(data["personas"])
    with t2:
        tab_promotion_sim(data["personas"], data["scenarios"])
    with t3:
        tab_analytics(data)
    with t4:
        tab_skill(data["personas"])
    with t5:
        tab_validation(data)
    with t6:
        tab_dialogue(data["personas"])
    with t7:
        tab_integrated_demo(data)


if __name__ == "__main__":
    main()
