"""Physician persona builder — transforms raw data into rich personas.

Follows the 'Persona Strategy' book methodology:
1. Extract factoids from data
2. Infer goals from behavioral patterns
3. Generate personality traits from response style
4. Assign a name, age, and catchphrase for 'realness'
"""

from __future__ import annotations

import hashlib
import random

from digital_twin.data.schema import (
    Factoid,
    PersonaGoal,
    PersonalityTrait,
    Physician,
    PromotionChannel,
    SurveyInstrument,
)
from digital_twin.persona.profile import HistoricalResponse, PhysicianPersona


# Japanese names for persona generation
_MALE_NAMES = [
    "田中 健一", "鈴木 雅之", "佐藤 和彦", "渡辺 誠", "伊藤 隆",
    "山本 浩二", "中村 大輔", "小林 正樹", "加藤 直樹", "吉田 拓也",
    "山田 英明", "松本 修一", "井上 慎吾", "木村 昌弘", "林 達也",
]

_FEMALE_NAMES = [
    "高橋 美咲", "山口 恵子", "中島 由美", "藤田 沙織", "岡田 真理",
    "前田 智子", "石井 朋子", "小川 裕子", "阿部 麻衣", "森 由佳",
]


class PersonaBuilder:
    """Builds PhysicianPersona objects from raw physician data."""

    def __init__(
        self,
        max_historical: int = 8,
        seed: int = 42,
    ) -> None:
        self.max_historical = max_historical
        self.rng = random.Random(seed)

    def build(
        self,
        physician: Physician,
        surveys: list[SurveyInstrument],
        training_survey_ids: list[str] | None = None,
    ) -> PhysicianPersona:
        """Build a complete physician persona from raw data."""

        persona_id = self._generate_persona_id(physician.physician_id)

        # Assign a realistic name
        name = self._assign_name(physician)
        age = self._infer_age(physician.demographics.age_group.value)

        # Extract factoids from data
        factoids = self._extract_factoids(physician)

        # Infer goals from behavior patterns
        goals = self._infer_goals(physician)

        # Generate personality traits
        traits = self._generate_personality_traits(physician)

        # Generate catchphrase
        catchphrase = self._generate_catchphrase(physician, traits)

        # Extract historical responses
        survey_map = {s.survey_id: s for s in surveys}
        historical = self._extract_historical_responses(
            physician, survey_map, training_survey_ids
        )

        persona = PhysicianPersona(
            persona_id=persona_id,
            name=name,
            age=age,
            gender=physician.demographics.gender.value,
            catchphrase=catchphrase,
            demographics=physician.demographics,
            prescription_profile=physician.prescription_profile,
            channel_preferences=physician.channel_preferences,
            goals=goals,
            factoids=factoids,
            personality_traits=traits,
            response_style=physician.response_style,
            promotion_history=physician.promotion_history,
            historical_responses=historical,
        )

        persona.persona_narrative = persona.to_system_prompt()

        return persona

    def build_batch(
        self,
        physicians: list[Physician],
        surveys: list[SurveyInstrument],
        training_survey_ids: list[str] | None = None,
    ) -> list[PhysicianPersona]:
        return [
            self.build(p, surveys, training_survey_ids)
            for p in physicians
        ]

    def _generate_persona_id(self, physician_id: str) -> str:
        h = hashlib.sha256(physician_id.encode()).hexdigest()[:12]
        return f"DR_{h}"

    def _assign_name(self, physician: Physician) -> str:
        if physician.demographics.gender.value == "male":
            return self.rng.choice(_MALE_NAMES)
        else:
            return self.rng.choice(_FEMALE_NAMES)

    def _infer_age(self, age_group: str) -> int:
        ranges = {
            "30-39": (32, 39),
            "40-49": (40, 49),
            "50-59": (50, 59),
            "60-69": (60, 69),
            "70+": (70, 75),
        }
        lo, hi = ranges.get(age_group, (45, 55))
        return self.rng.randint(lo, hi)

    def _extract_factoids(self, physician: Physician) -> list[Factoid]:
        """Extract factoids from the physician's actual data."""
        factoids = []

        # From prescription profile
        rx = physician.prescription_profile
        if rx.primary_drugs:
            factoids.append(Factoid(
                category="behavior",
                content=f"{rx.therapeutic_area}領域で主に{', '.join(rx.primary_drugs)}を処方している",
                data_source="Doctor Mindscape",
            ))

        if rx.new_drug_adoption_speed == "early":
            factoids.append(Factoid(
                category="preference",
                content="新薬には積極的で、エビデンスが出ればすぐに採用を検討する",
                data_source="処方データ",
            ))
        elif rx.new_drug_adoption_speed == "late":
            factoids.append(Factoid(
                category="preference",
                content="新薬の採用には慎重で、十分な実績を確認してから処方を始める",
                data_source="処方データ",
            ))

        # From channel preferences
        preferred_channels = [
            cp for cp in physician.channel_preferences if cp.preferred
        ]
        if preferred_channels:
            ch_names = [cp.channel.value for cp in preferred_channels]
            factoids.append(Factoid(
                category="preference",
                content=f"情報収集は主に{', '.join(ch_names)}を好む",
                data_source="Impact Track",
            ))

        # From promotion history
        if physician.promotion_history:
            recent = physician.promotion_history[-5:]
            companies = set(e.pharma_company for e in recent)
            factoids.append(Factoid(
                category="behavior",
                content=f"最近は{', '.join(companies)}のプロモーションを受けている",
                data_source="Impact Track",
            ))

        # From response style
        if physician.response_style.mr_receptivity == "reserved":
            factoids.append(Factoid(
                category="frustration",
                content="多忙でMRとの面談は短時間で済ませたい。要点を絞った情報提供を求める",
                data_source="行動データ",
            ))

        # Use pre-existing factoids from data
        factoids.extend(physician.factoids)

        return factoids

    def _infer_goals(self, physician: Physician) -> list[PersonaGoal]:
        """Infer persona goals from behavioral data."""
        goals = []

        rx = physician.prescription_profile

        # Clinical goals
        goals.append(PersonaGoal(
            goal_type="clinical",
            description=f"{rx.therapeutic_area}の患者に最適な治療を提供したい",
            priority=1,
        ))

        if rx.guideline_adherence == "strict":
            goals.append(PersonaGoal(
                goal_type="clinical",
                description="エビデンスとガイドラインに基づいた治療選択を徹底したい",
                priority=2,
            ))

        # Career goals
        demo = physician.demographics
        if demo.is_key_opinion_leader:
            goals.append(PersonaGoal(
                goal_type="career",
                description="研究成果を学会で発表し、領域の第一人者としての地位を維持したい",
                priority=2,
            ))
        elif demo.years_of_experience < 15:
            goals.append(PersonaGoal(
                goal_type="career",
                description="専門性を高め、指導医として後進の育成にも貢献したい",
                priority=3,
            ))

        # Product/information goals
        if rx.new_drug_adoption_speed == "early":
            goals.append(PersonaGoal(
                goal_type="product",
                description="新薬の臨床データをいち早く入手し、患者に最先端の治療を届けたい",
                priority=2,
            ))
        else:
            goals.append(PersonaGoal(
                goal_type="product",
                description="安全性の高い実績ある治療法を中心に処方を組み立てたい",
                priority=2,
            ))

        # Use pre-existing goals from data
        goals.extend(physician.goals)

        return goals

    def _generate_personality_traits(self, physician: Physician) -> list[PersonalityTrait]:
        """Generate personality traits from response style and behavior."""
        traits = []

        style = physician.response_style

        if style.scale_usage.value == "extreme":
            traits.append(PersonalityTrait(
                trait_name="明確な態度",
                description="物事に対して白黒はっきりした意見を持つ。曖昧な表現を避ける傾向がある",
            ))
        elif style.scale_usage.value == "moderate":
            traits.append(PersonalityTrait(
                trait_name="慎重さ",
                description="判断を急がず、多角的に検討してから意見を述べる。断定的な表現は避ける",
            ))
        elif style.scale_usage.value == "acquiescent":
            traits.append(PersonalityTrait(
                trait_name="協調性",
                description="相手の話をよく聞き、基本的に前向きに受け止める姿勢を持つ",
            ))

        if style.mr_receptivity == "reserved":
            traits.append(PersonalityTrait(
                trait_name="効率重視",
                description="時間に厳しく、短時間で要点を把握したい。無駄な説明は苦手",
            ))
        elif style.mr_receptivity == "open":
            traits.append(PersonalityTrait(
                trait_name="対話好き",
                description="MRとのディスカッションを通じて情報収集するのが好き。質問も多い",
            ))

        rx = physician.prescription_profile
        if rx.prescribing_philosophy:
            traits.append(PersonalityTrait(
                trait_name="処方哲学",
                description=rx.prescribing_philosophy,
            ))

        # Use pre-existing traits
        traits.extend(physician.personality_traits)

        return traits

    def _generate_catchphrase(
        self,
        physician: Physician,
        traits: list[PersonalityTrait],
    ) -> str:
        """Generate a catchphrase that captures the persona's essence."""
        rx = physician.prescription_profile
        demo = physician.demographics

        templates = {
            ("early", "open"): f"「新しいエビデンスが出たらすぐに検討したい。{rx.therapeutic_area}の患者さんのために」",
            ("early", "reserved"): f"「データを見せてくれ。良ければすぐ採用する」",
            ("late", "open"): f"「じっくり話を聞くが、処方を変えるにはしっかりした根拠が必要だ」",
            ("late", "reserved"): f"「安全性データが十分に蓄積されてから判断したい」",
            ("moderate", "open"): f"「バランスよく情報収集して、患者にとってベストな選択をしたい」",
            ("moderate", "reserved"): f"「忙しいが、{rx.therapeutic_area}の最新動向は押さえておきたい」",
            ("moderate", "moderate"): f"「エビデンスと臨床経験の両方を大事にしたい」",
        }

        key = (rx.new_drug_adoption_speed, physician.response_style.mr_receptivity)
        return templates.get(key, f"「{rx.therapeutic_area}の患者さんに最善の医療を」")

    def _extract_historical_responses(
        self,
        physician: Physician,
        survey_map: dict[str, SurveyInstrument],
        training_survey_ids: list[str] | None,
    ) -> list[HistoricalResponse]:
        """Extract historical responses as few-shot examples."""
        historical: list[HistoricalResponse] = []

        for sr in physician.survey_responses:
            if training_survey_ids and sr.survey_id not in training_survey_ids:
                continue

            survey = survey_map.get(sr.survey_id)
            if not survey:
                continue

            question_map = {q.question_id: q for q in survey.questions}

            for qr in sr.responses:
                q = question_map.get(qr.question_id)
                if not q:
                    continue

                historical.append(HistoricalResponse(
                    question_text=q.question_text,
                    question_category=q.category,
                    response_value=qr.response_value,
                    free_text=qr.free_text,
                ))

        # Diversify by category
        if len(historical) > self.max_historical:
            by_cat: dict[str, list[HistoricalResponse]] = {}
            for h in historical:
                by_cat.setdefault(h.question_category, []).append(h)
            selected: list[HistoricalResponse] = []
            cats = list(by_cat.keys())
            idx = 0
            while len(selected) < self.max_historical and any(by_cat.values()):
                cat = cats[idx % len(cats)]
                if by_cat.get(cat):
                    selected.append(by_cat[cat].pop(0))
                idx += 1
                cats = [c for c in cats if by_cat.get(c)]
            return selected

        return historical
