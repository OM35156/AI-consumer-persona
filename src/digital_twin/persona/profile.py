"""Physician persona profile — based on 'Persona Strategy' book methodology.

A persona is not an abstract "user type" but a specific, named individual
with goals, factoids, personality quirks, and a face. The persona speaks
in first person and represents a real pattern found in the data.

Key concepts from the book:
- Identification: Name, age, catchphrase
- Goals: Short-term and long-term objectives
- Factoids: Data-backed behavioral facts
- Situation & Environment: Devices, schedule, physical setting
- Psychological Details: Values, fears, frustrations, quirks
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from digital_twin.data.schema import (
    ChannelPreference,
    Factoid,
    PersonaGoal,
    PersonalityTrait,
    PhysicianDemographics,
    PrescriptionProfile,
    PromotionExposure,
    ResponseStyle,
)


class PhysicianPersona(BaseModel):
    """Complete physician persona — 'a specific someone'.

    This is the core data structure that feeds into the LLM prompt.
    The persona should feel like a real person that development teams
    can empathize with and use as a decision-making tool.
    """

    # --- Identification (識別情報) ---
    persona_id: str
    name: str  # 実在感のある日本語フルネーム
    age: int
    gender: str
    catchphrase: str = ""  # このペルソナを象徴する一言

    # --- Professional Profile ---
    demographics: PhysicianDemographics
    prescription_profile: PrescriptionProfile
    channel_preferences: list[ChannelPreference] = []

    # --- Persona Strategy Components ---
    goals: list[PersonaGoal] = []
    factoids: list[Factoid] = []
    personality_traits: list[PersonalityTrait] = []

    # --- Response Style ---
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)

    # --- Historical Data ---
    promotion_history: list[PromotionExposure] = []
    historical_responses: list[HistoricalResponse] = []

    # --- Generated Narrative ---
    persona_narrative: str = ""

    def to_system_prompt(
        self,
        segment_profile_text: str | None = None,
        rag_context: str | None = None,
    ) -> str:
        """Generate the full system prompt for this persona.

        Following the 'Persona Strategy' book: the AI IS this person,
        speaking in first person, with specific quirks and constraints.

        Args:
            segment_profile_text: 層①セグメントプロファイルのテキスト（オプション）
            rag_context: 層②RAG検索結果のコンテキスト（オプション）
        """
        sections = []

        # Role definition
        sections.append(self._build_role_section())

        # Knowledge context (persona document)
        sections.append(self._build_knowledge_section())

        # Layer ①: Segment profile (if provided)
        if segment_profile_text:
            sections.append(segment_profile_text)

        # Layer ②: RAG context (if provided)
        if rag_context:
            sections.append(rag_context)

        # Skills/capabilities
        sections.append(self._build_skills_section())

        # Constraints
        sections.append(self._build_constraints_section())

        return "\n\n".join(sections)

    def _build_role_section(self) -> str:
        return f"""# Role
あなたは{self.name}（{self.age}歳）です。{self.catchphrase}

あなたは抽象的な「医師ユーザー」ではなく、実在する医師データから構築された、
名前、個人的な目標、固有の癖を持つ「特定の誰か」として振る舞います。

製品開発チームや製薬企業との対話において、提示された薬剤情報やプロモーションに対し、
自身の「ゴール」と「背景」に照らして、一人の医師としての率直な反応を示してください。"""

    def _build_knowledge_section(self) -> str:
        demo = self.demographics
        rx = self.prescription_profile

        lines = [
            "# Knowledge Context（基本文書）",
            "",
            "## 識別情報",
            f"- 名前: {self.name}",
            f"- 年齢: {self.age}歳",
            f"- 性別: {'男性' if self.gender == 'male' else '女性'}",
            f"- 診療科: {_specialty_ja(demo.specialty.value)}",
            f"- 勤務先: {_facility_ja(demo.facility_type.value)}（{_region_ja(demo.region.value)}）",
            f"- 経験年数: {demo.years_of_experience}年",
            f"- 月間患者数: 約{demo.patients_per_month}名",
            f"- KOL: {'はい' if demo.is_key_opinion_leader else 'いいえ'}",
        ]

        # Goals
        if self.goals:
            lines.append("\n## ゴール (Goals)")
            for g in self.goals:
                priority_mark = "★" * (6 - g.priority)
                lines.append(f"- [{g.goal_type}] {g.description} {priority_mark}")

        # Factoids
        if self.factoids:
            lines.append("\n## ファクトイド (Factoids)")
            for f in self.factoids:
                source = f" ({f.data_source})" if f.data_source else ""
                lines.append(f"- [{f.category}] {f.content}{source}")

        # Prescription profile
        lines.append("\n## 処方行動")
        lines.append(f"- 対象疾患領域: {rx.therapeutic_area}")
        if rx.primary_drugs:
            lines.append(f"- 主要処方薬: {', '.join(rx.primary_drugs)}")
        if rx.drug_prescription_status:
            for drug, status in rx.drug_prescription_status.items():
                lines.append(f"  - {drug}: {_rx_status_ja(status.value)}")
        lines.append(f"- 処方哲学: {rx.prescribing_philosophy}")
        guideline_ja = {"strict": "厳格に遵守", "moderate": "基本的に遵守", "flexible": "柔軟に適用"}
        lines.append(f"- ガイドライン遵守: {guideline_ja.get(rx.guideline_adherence, rx.guideline_adherence)}")
        adoption_ja = {"early": "アーリーアダプター", "moderate": "標準的", "late": "慎重派"}
        lines.append(f"- 新薬採用速度: {adoption_ja.get(rx.new_drug_adoption_speed, rx.new_drug_adoption_speed)}")

        # Channel preferences
        if self.channel_preferences:
            lines.append("\n## 情報チャネル嗜好性")
            for cp in sorted(self.channel_preferences, key=lambda x: -x.receptivity):
                ch_name = _channel_ja(cp.channel.value)
                stars = "●" * cp.receptivity + "○" * (5 - cp.receptivity)
                lines.append(f"- {ch_name}: {stars} (月{cp.frequency_per_month}回)")

        # Personality
        if self.personality_traits:
            lines.append("\n## 心理的詳細・性格")
            for t in self.personality_traits:
                lines.append(f"- {t.trait_name}: {t.description}")

        # Response style
        style = self.response_style
        lines.append("\n## 回答スタイル")
        style_desc = {
            "extreme": "はっきりとした態度を示す",
            "moderate": "慎重な中間的回答が多い",
            "acquiescent": "概ね肯定的に応じる傾向",
            "balanced": "公平でバランスの取れた評価をする",
        }
        lines.append(f"- 尺度回答傾向: {style_desc.get(style.scale_usage.value, style.scale_usage.value)}")
        mr_desc = {"open": "オープンで話しやすい", "moderate": "標準的", "reserved": "多忙でMRとの面談は短め"}
        lines.append(f"- MRへの態度: {mr_desc.get(style.mr_receptivity, style.mr_receptivity)}")
        verbosity = {"low": "簡潔・端的", "medium": "適度な詳しさ", "high": "詳細で論理的"}
        lines.append(f"- 発言の詳しさ: {verbosity.get(style.free_text_verbosity, style.free_text_verbosity)}")

        return "\n".join(lines)

    def _build_skills_section(self) -> str:
        return """# Skills / Capabilities
あなたは以下の機能を提供します：

1. **ペルソナ視点でのフィードバック**: 「私はこの薬を処方したいか？」「このメッセージは響くか？」を自身のゴールに照らして回答
2. **シナリオのウォークスルー**: MR訪問やWeb講演会の場面を、自分の日常の中で一人称で描写
3. **処方意向の判定**: プロモーション提示後の処方意向を「増やしたい/現状維持/減らしたい/新規採用したい/処方予定なし」で判定
4. **機能評価**: 提示された施策が自分にとって「喜ぶ(+2)/役立つ(+1)/無関心(0)/困惑する(-1)」を判定
5. **競合分析**: 競合製品の情報を聞いた時の率直な反応を述べる"""

    def _build_constraints_section(self) -> str:
        return """# Constraints / Style

- **一人称での対話**: 常に「私は〜」で話す。「この医師は〜」という三人称の分析は禁止
- **データへの忠実性**: 自分の意見はファクトイドの範囲内。データにない「想像上の便利さ」は肯定しない
- **万人受けの否定**: 「私には不要だが他の医師には必要かもしれない」という妥協はしない。あくまで自分にとっての価値を主張
- **具体的な細部**: 「便利そう」でなく「水曜の外来の合間にMRから5分で聞くなら、このデータの見せ方は良い」と語る
- **処方行動の一貫性**: 自分の処方哲学・新薬採用速度・ガイドライン遵守度と矛盾しない判断をする"""

    def get_promotion_history_summary(self, max_entries: int = 5) -> str:
        """Format recent promotion exposure history."""
        if not self.promotion_history:
            return ""

        lines = ["## 最近のプロモーション接触履歴"]
        for exp in self.promotion_history[-max_entries:]:
            ch = _channel_ja(exp.channel.value)
            intent_ja = _intent_ja(exp.prescription_intent_after.value)
            lines.append(
                f"- [{exp.date}] {exp.pharma_company} {exp.product_name} "
                f"via {ch} → 処方意向: {intent_ja}"
            )
            if exp.detail_content:
                lines.append(f"  内容: {exp.detail_content}")

        return "\n".join(lines)

    def get_few_shot_examples(self, max_examples: int = 5) -> str:
        """Format historical responses as few-shot examples."""
        if not self.historical_responses:
            return ""

        examples = self.historical_responses[:max_examples]
        lines = ["## 過去の回答例"]
        for ex in examples:
            lines.append(f"\nQ: {ex.question_text}")
            if ex.response_value is not None:
                if isinstance(ex.response_value, list):
                    lines.append(f"A: {', '.join(str(v) for v in ex.response_value)}")
                else:
                    lines.append(f"A: {ex.response_value}")
            if ex.free_text:
                lines.append(f"A（コメント）: {ex.free_text}")

        return "\n".join(lines)

    def to_skill_md(self) -> str:
        """Generate a skill.md file for this persona."""
        return f"""---
name: {self.name}
description: {self.catchphrase}
type: physician_persona
---

{self.to_system_prompt()}

# Evaluation Criteria
- **会議の強力な発言者か？** 開発者が「{self.name}先生ならどう言うだろう？」と想像できる個性があるか
- **設計に制約を与えるか？** 私の特性により「この施策はやめよう」と判断できる材料を提供できるか
- **実在感があるか？** チームが感情移入し、実在の医師のように扱いたくなる像を描けるか
"""


class HistoricalResponse(BaseModel):
    """過去の調査回答（few-shot例）"""
    question_text: str
    question_category: str
    response_value: str | int | float | list[str] | None = None
    free_text: str | None = None


# --- Helper functions ---


def _specialty_ja(specialty: str) -> str:
    return {
        "oncology": "腫瘍内科",
        "surgery": "外科",
        "breast_surgery": "乳腺外科",
        "respiratory": "呼吸器内科",
        "gastroenterology": "消化器内科",
        "urology": "泌尿器科",
        "hematology": "血液内科",
        "gynecology": "婦人科",
        "general_internal": "一般内科",
    }.get(specialty, specialty)


def _facility_ja(facility: str) -> str:
    return {
        "university_hospital": "大学病院",
        "general_hospital": "総合病院",
        "specialized_hospital": "専門病院",
        "clinic": "クリニック",
        "cancer_center": "がんセンター",
    }.get(facility, facility)


def _region_ja(region: str) -> str:
    return {
        "hokkaido": "北海道",
        "tohoku": "東北",
        "kanto": "関東",
        "chubu": "中部",
        "kinki": "近畿",
        "chugoku": "中国",
        "shikoku": "四国",
        "kyushu": "九州",
    }.get(region, region)


def _channel_ja(channel: str) -> str:
    return {
        "mr_detail": "MRディテール",
        "mr_briefing": "MR院内説明会",
        "online_meeting": "オンライン面談",
        "web_lecture": "Web講演会",
        "live_lecture": "講演会（リアル）",
        "internet": "インターネット",
        "journal": "学術雑誌",
    }.get(channel, channel)


def _rx_status_ja(status: str) -> str:
    return {
        "active_prescriber": "現在処方中",
        "past_prescriber": "過去に処方",
        "aware_not_prescribed": "認知あり・未処方",
        "unaware": "非認知",
    }.get(status, status)


def _intent_ja(intent: str) -> str:
    return {
        "increase": "増やしたい",
        "maintain": "現状維持",
        "decrease": "減らしたい",
        "start": "新規採用したい",
        "no_intent": "処方予定なし",
    }.get(intent, intent)
