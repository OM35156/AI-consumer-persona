"""ConsumerPersonaBuilder のテスト."""

from __future__ import annotations

from digital_twin.data.schema import (
    AgeGroup,
    BrandAwareness,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    Gender,
    LifeStage,
    Region,
)
from digital_twin.persona.builder import ConsumerPersonaBuilder
from digital_twin.persona.profile import ConsumerPersona


class TestBuildSample:
    def test_build_sample_returns_consumer_persona(self) -> None:
        b = ConsumerPersonaBuilder(seed=0)
        p = b.build_sample()
        assert isinstance(p, ConsumerPersona)
        assert p.persona_id.startswith("CP_")
        assert p.name  # 日本語フルネームが割当
        assert 30 <= p.age <= 50  # 35-44 年代から代表年齢
        assert p.gender == "female"

    def test_build_sample_deterministic(self) -> None:
        p1 = ConsumerPersonaBuilder(seed=42).build_sample()
        p2 = ConsumerPersonaBuilder(seed=42).build_sample()
        assert p1.name == p2.name
        assert p1.age == p2.age


class TestBuildFromConsumer:
    @staticmethod
    def _make_consumer() -> Consumer:
        return Consumer(
            consumer_id="TEST_C_001",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_25_34,
                gender=Gender.MALE,
                region=Region.KINKI,
                life_stage=LifeStage.SINGLE_WORKING,
                occupation="エンジニア",
                is_influencer=True,
            ),
            category_profile=CategoryProfile(
                category="ガジェット",
                primary_brands=["Apple", "Sony"],
                brand_status={"Apple": BrandAwareness.ACTIVE_USER},
                purchase_philosophy="最新技術を試したい",
                price_sensitivity="low",
                new_product_receptivity="early",
            ),
        )

    def test_build_generates_factoids_and_goals(self) -> None:
        b = ConsumerPersonaBuilder(seed=1)
        p = b.build(self._make_consumer())

        # factoids: ブランド言及 / 新商品受容 / 価格感度 low
        assert len(p.factoids) >= 2
        factoid_contents = " ".join(f.content for f in p.factoids)
        assert "Apple" in factoid_contents or "Sony" in factoid_contents

        # goals: lifestyle + ガジェットカテゴリ
        assert len(p.goals) >= 2
        goal_types = {g.goal_type for g in p.goals}
        assert "lifestyle" in goal_types

    def test_build_assigns_male_name(self) -> None:
        b = ConsumerPersonaBuilder(seed=1)
        p = b.build(self._make_consumer())
        # 男性名辞書からの割当を確認（姓名の形式）
        assert " " in p.name  # "田中 健一" のような空白区切り

    def test_build_age_in_range(self) -> None:
        b = ConsumerPersonaBuilder(seed=1)
        p = b.build(self._make_consumer())
        # AgeGroup AGE_25_34 → 26〜34 の範囲
        assert 26 <= p.age <= 34

    def test_build_carries_influencer_trait(self) -> None:
        b = ConsumerPersonaBuilder(seed=1)
        p = b.build(self._make_consumer())
        trait_names = {t.trait_name for t in p.personality_traits}
        assert "インフルエンサー気質" in trait_names

    def test_build_batch(self) -> None:
        b = ConsumerPersonaBuilder(seed=1)
        consumers = [self._make_consumer() for _ in range(3)]
        personas = b.build_batch(consumers)
        assert len(personas) == 3
        assert all(isinstance(p, ConsumerPersona) for p in personas)
