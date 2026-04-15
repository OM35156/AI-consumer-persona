"""Consumer persona builder — transforms raw consumer data into rich personas.

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
    AgeGroup,
    BrandAwareness,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    Factoid,
    Gender,
    LifeStage,
    PersonaGoal,
    PersonalityTrait,
    Region,
    SurveyInstrument,
)
from digital_twin.persona.profile import ConsumerPersona, HistoricalResponse


# 生活者ペルソナ用の日本語フルネーム候補
_MALE_NAMES = [
    "田中 健一", "鈴木 雅之", "佐藤 和彦", "渡辺 誠", "伊藤 隆",
    "山本 浩二", "中村 大輔", "小林 正樹", "加藤 直樹", "吉田 拓也",
    "山田 英明", "松本 修一", "井上 慎吾", "木村 昌弘", "林 達也",
]

_FEMALE_NAMES = [
    "高橋 美咲", "山口 恵子", "中島 由美", "藤田 沙織", "岡田 真理",
    "前田 智子", "石井 朋子", "小川 裕子", "阿部 麻衣", "森 由佳",
    "清水 綾香", "池田 香織", "橋本 美穂", "斎藤 理恵", "青木 愛",
]


class ConsumerPersonaBuilder:
    """生活者 Consumer データから ConsumerPersona オブジェクトを構築する."""

    def __init__(
        self,
        max_historical: int = 8,
        seed: int = 42,
    ) -> None:
        self.max_historical = max_historical
        self.rng = random.Random(seed)

    def build(
        self,
        consumer: Consumer,
        surveys: list[SurveyInstrument] | None = None,
        training_survey_ids: list[str] | None = None,
    ) -> ConsumerPersona:
        """生データから完全な生活者ペルソナを構築する."""
        persona_id = self._generate_persona_id(consumer.consumer_id)

        # Assign a realistic name
        name = self._assign_name(consumer)
        age = self._infer_age(consumer.demographics.age_group.value)

        # Extract factoids from data
        factoids = self._extract_factoids(consumer)

        # Infer goals from behavior patterns
        goals = self._infer_goals(consumer)

        # Generate personality traits
        traits = self._generate_personality_traits(consumer)

        # Generate catchphrase
        catchphrase = self._generate_catchphrase(consumer, traits)

        # Extract historical responses (surveys が与えられた場合のみ)
        historical: list[HistoricalResponse] = []
        if surveys:
            survey_map = {s.survey_id: s for s in surveys}
            historical = self._extract_historical_responses(
                consumer, survey_map, training_survey_ids
            )

        persona = ConsumerPersona(
            persona_id=persona_id,
            name=name,
            age=age,
            gender=consumer.demographics.gender.value,
            catchphrase=catchphrase,
            demographics=consumer.demographics,
            category_profile=consumer.category_profile,
            channel_preferences=consumer.channel_preferences,
            goals=goals,
            factoids=factoids,
            personality_traits=traits,
            response_style=consumer.response_style,
            brand_history=consumer.brand_history,
            historical_responses=historical,
        )

        persona.persona_narrative = persona.to_system_prompt()

        return persona

    def build_batch(
        self,
        consumers: list[Consumer],
        surveys: list[SurveyInstrument] | None = None,
        training_survey_ids: list[str] | None = None,
    ) -> list[ConsumerPersona]:
        return [
            self.build(c, surveys, training_survey_ids)
            for c in consumers
        ]

    def build_sample(self) -> ConsumerPersona:
        """デモ・テスト用に最小構成のサンプルペルソナを生成する."""
        sample_consumer = Consumer(
            consumer_id="SAMPLE_001",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE,
                region=Region.KANTO,
                life_stage=LifeStage.MARRIED_WITH_CHILDREN,
                occupation="会社員",
                household_income="600-800万円",
            ),
            category_profile=CategoryProfile(
                category="スキンケア",
                primary_brands=["資生堂", "ロート製薬"],
                brand_status={"資生堂": BrandAwareness.ACTIVE_USER},
                purchase_philosophy="品質と実績を重視、子育てと両立できる時短ケアを探している",
                price_sensitivity="moderate",
                new_product_receptivity="moderate",
            ),
        )
        return self.build(sample_consumer)

    def _generate_persona_id(self, consumer_id: str) -> str:
        h = hashlib.sha256(consumer_id.encode()).hexdigest()[:12]
        return f"CP_{h}"

    def _assign_name(self, consumer: Consumer) -> str:
        if consumer.demographics.gender.value == "male":
            return self.rng.choice(_MALE_NAMES)
        return self.rng.choice(_FEMALE_NAMES)

    def _infer_age(self, age_group: str) -> int:
        """AgeGroup enum の value から代表年齢をランダムに割り当てる."""
        ranges = {
            "18-24": (19, 24),
            "25-34": (26, 34),
            "35-44": (36, 44),
            "45-54": (46, 54),
            "55-64": (56, 64),
            "65+": (66, 74),
        }
        lo, hi = ranges.get(age_group, (30, 45))
        return self.rng.randint(lo, hi)

    def _extract_factoids(self, consumer: Consumer) -> list[Factoid]:
        """生活者の実データからファクトイドを抽出する."""
        factoids: list[Factoid] = []
        cat = consumer.category_profile

        # From category profile
        if cat.primary_brands:
            factoids.append(Factoid(
                category="behavior",
                content=f"{cat.category}では主に{', '.join(cat.primary_brands)}を利用している",
                data_source="購買履歴",
            ))

        if cat.new_product_receptivity == "early":
            factoids.append(Factoid(
                category="preference",
                content=f"{cat.category}の新商品には敏感で、話題になればすぐに試してみる",
                data_source="購買履歴",
            ))
        elif cat.new_product_receptivity == "late":
            factoids.append(Factoid(
                category="preference",
                content=f"{cat.category}の新商品には慎重で、口コミや評判を確認してから試す",
                data_source="購買履歴",
            ))

        if cat.price_sensitivity == "high":
            factoids.append(Factoid(
                category="preference",
                content="価格に敏感で、同等品があれば必ず安い方を選ぶ",
                data_source="購買履歴",
            ))
        elif cat.price_sensitivity == "low":
            factoids.append(Factoid(
                category="preference",
                content="多少高くても品質や実績のある商品を選ぶ",
                data_source="購買履歴",
            ))

        # From channel preferences
        preferred_channels = [
            cp for cp in consumer.channel_preferences if cp.preferred
        ]
        if preferred_channels:
            ch_names = [cp.channel.value for cp in preferred_channels]
            factoids.append(Factoid(
                category="preference",
                content=f"情報収集は主に {', '.join(ch_names)} を好む",
                data_source="メディア接触調査",
            ))

        # From brand history
        if consumer.brand_history:
            recent = consumer.brand_history[-5:]
            brands = {e.brand_name for e in recent}
            factoids.append(Factoid(
                category="behavior",
                content=f"最近は {', '.join(brands)} の広告に接触している",
                data_source="広告接触ログ",
            ))

        # From response style
        if consumer.response_style.survey_receptivity == "low":
            factoids.append(Factoid(
                category="frustration",
                content="アンケートには淡白で、長文の質問には答えず要点だけ返す傾向がある",
                data_source="回答スタイル分析",
            ))

        # ライフステージ由来の追加ファクトイド
        life_stage = consumer.demographics.life_stage.value
        if life_stage == "married_with_children":
            factoids.append(Factoid(
                category="situation",
                content="子育て中で日々忙しく、買い物や情報収集の時間は限られている",
                data_source="ライフステージ",
            ))
        elif life_stage == "retired":
            factoids.append(Factoid(
                category="situation",
                content="退職後で時間にゆとりがあり、じっくり比較検討してから購入する",
                data_source="ライフステージ",
            ))

        # Use pre-existing factoids from data
        factoids.extend(consumer.factoids)

        return factoids

    def _infer_goals(self, consumer: Consumer) -> list[PersonaGoal]:
        """行動データからペルソナのゴールを推論する."""
        goals: list[PersonaGoal] = []
        cat = consumer.category_profile
        life_stage = consumer.demographics.life_stage.value

        # ライフスタイル軸のゴール
        if life_stage == "married_with_children":
            goals.append(PersonaGoal(
                goal_type="lifestyle",
                description="家族の生活を快適にしつつ、自分の時間も確保したい",
                priority=1,
            ))
        elif life_stage == "single_working":
            goals.append(PersonaGoal(
                goal_type="lifestyle",
                description="仕事とプライベートを充実させ、自分らしい生活を送りたい",
                priority=1,
            ))
        elif life_stage == "retired":
            goals.append(PersonaGoal(
                goal_type="lifestyle",
                description="健康を維持しながら、趣味や家族と過ごす時間を大切にしたい",
                priority=1,
            ))
        else:
            goals.append(PersonaGoal(
                goal_type="lifestyle",
                description="日々の生活をより良くするための選択をしたい",
                priority=2,
            ))

        # カテゴリ軸のゴール
        category_lower = cat.category.lower()
        if any(kw in category_lower for kw in ["スキン", "化粧", "美容", "beauty"]):
            goals.append(PersonaGoal(
                goal_type="beauty",
                description=f"{cat.category}で自分に合う商品を見つけ、自信を持って過ごしたい",
                priority=2,
            ))
        elif any(kw in category_lower for kw in ["健康", "サプリ", "health"]):
            goals.append(PersonaGoal(
                goal_type="health",
                description=f"{cat.category}を通じて健康維持・向上を図りたい",
                priority=2,
            ))
        else:
            goals.append(PersonaGoal(
                goal_type="lifestyle",
                description=f"{cat.category}で納得のいく選択をしたい",
                priority=3,
            ))

        # 価格感度軸のゴール
        if cat.price_sensitivity == "high":
            goals.append(PersonaGoal(
                goal_type="savings",
                description="賢くお得に買い物をして、家計の負担を減らしたい",
                priority=2,
            ))

        # Use pre-existing goals from data
        goals.extend(consumer.goals)

        return goals

    def _generate_personality_traits(self, consumer: Consumer) -> list[PersonalityTrait]:
        """回答スタイルと行動から性格特性を生成する."""
        traits: list[PersonalityTrait] = []
        style = consumer.response_style
        cat = consumer.category_profile

        # Scale usage → 意見表明の強さ
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
        elif style.scale_usage.value == "balanced":
            traits.append(PersonalityTrait(
                trait_name="バランス感覚",
                description="良い面と悪い面の両方を冷静に評価し、偏りのない判断をする",
            ))

        # Survey receptivity → 情報発信の積極性
        if style.survey_receptivity == "low":
            traits.append(PersonalityTrait(
                trait_name="効率重視",
                description="時間を無駄にしたくない。長い質問やアンケートは最小限で済ませたい",
            ))
        elif style.survey_receptivity == "high":
            traits.append(PersonalityTrait(
                trait_name="発信好き",
                description="自分の意見や体験を共有するのが好き。アンケートや口コミに積極的",
            ))

        # Purchase philosophy をそのまま trait として保持
        if cat.purchase_philosophy:
            traits.append(PersonalityTrait(
                trait_name="購買哲学",
                description=cat.purchase_philosophy,
            ))

        # Influencer 傾向
        if consumer.demographics.is_influencer:
            traits.append(PersonalityTrait(
                trait_name="インフルエンサー気質",
                description="SNSで発信する機会が多く、自分の選択が周囲に影響を与えると感じている",
            ))

        # Use pre-existing traits
        traits.extend(consumer.personality_traits)

        return traits

    def _generate_catchphrase(
        self,
        consumer: Consumer,
        traits: list[PersonalityTrait],
    ) -> str:
        """ペルソナの本質を表すキャッチフレーズを生成する."""
        cat = consumer.category_profile
        life_stage = consumer.demographics.life_stage.value

        # (life_stage, new_product_receptivity) で分岐
        templates = {
            ("married_with_children", "early"): "「忙しいけど、良い商品があれば家族のためにすぐ試したい」",
            ("married_with_children", "late"): "「家族に使うものは口コミと実績を確認してから選びたい」",
            ("married_with_children", "moderate"): "「家族の生活を少しでも快適にできる商品を見つけたい」",
            ("single_working", "early"): "「気になったものはすぐ試す。仕事で疲れた自分へのご褒美も忘れない」",
            ("single_working", "late"): "「独り暮らしは自分の判断が全て。失敗したくないから慎重に選ぶ」",
            ("single_working", "moderate"): "「仕事も生活もバランスよく、自分に合うものを選びたい」",
            ("student", "early"): "「SNSで話題のものはとりあえずチェック、合えばリピートする」",
            ("retired", "late"): "「じっくり比べて、長く付き合える商品を選びたい」",
            ("retired", "moderate"): "「余裕のある時間で、納得のいく買い物をしたい」",
            ("empty_nest", "moderate"): "「子育てが一段落した今、自分のための選択を楽しみたい」",
        }

        key = (life_stage, cat.new_product_receptivity)
        return templates.get(key, f"「{cat.category}で自分らしい選択をしたい」")

    def _extract_historical_responses(
        self,
        consumer: Consumer,
        survey_map: dict[str, SurveyInstrument],
        training_survey_ids: list[str] | None,
    ) -> list[HistoricalResponse]:
        """過去の調査回答を few-shot 例として抽出する."""
        historical: list[HistoricalResponse] = []

        for sr in consumer.survey_responses:
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
                cat_key = cats[idx % len(cats)]
                if by_cat.get(cat_key):
                    selected.append(by_cat[cat_key].pop(0))
                idx += 1
                cats = [c for c in cats if by_cat.get(c)]
            return selected

        return historical
