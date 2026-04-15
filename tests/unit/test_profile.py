"""ConsumerPersona のテスト."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from digital_twin.data.schema import (
    AgeGroup,
    BrandAwareness,
    CategoryProfile,
    ConsumerDemographics,
    Factoid,
    Gender,
    LifeStage,
    PersonaGoal,
    Region,
)
from digital_twin.persona.profile import ConsumerPersona, HistoricalResponse


def _make_demo() -> ConsumerDemographics:
    return ConsumerDemographics(
        age_group=AgeGroup.AGE_35_44,
        gender=Gender.FEMALE,
        region=Region.KANTO,
        life_stage=LifeStage.MARRIED_WITH_CHILDREN,
    )


def _make_cat() -> CategoryProfile:
    return CategoryProfile(
        category="スキンケア",
        primary_brands=["資生堂"],
        brand_status={"資生堂": BrandAwareness.ACTIVE_USER},
        purchase_philosophy="品質重視",
        price_sensitivity="moderate",
        new_product_receptivity="moderate",
    )


class TestConsumerPersona:
    def test_minimal_build(self) -> None:
        p = ConsumerPersona(
            persona_id="t1",
            name="山田 花子",
            age=38,
            gender="female",
            demographics=_make_demo(),
            category_profile=_make_cat(),
        )
        assert p.persona_id == "t1"
        assert p.name == "山田 花子"
        assert p.goals == []
        assert p.catchphrase == ""

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ConsumerPersona(  # type: ignore[call-arg]
                persona_id="t1",
                name="A",
                age=30,
                gender="male",
                # demographics / category_profile 欠落
            )

    def test_to_system_prompt_contains_persona_info(self) -> None:
        p = ConsumerPersona(
            persona_id="t2",
            name="山田 花子",
            age=38,
            gender="female",
            catchphrase="忙しくても自分の時間を大切にしたい",
            demographics=_make_demo(),
            category_profile=_make_cat(),
            goals=[PersonaGoal(goal_type="beauty", description="肌悩みを減らしたい")],
            factoids=[Factoid(category="behavior", content="毎朝スキンケアをしている")],
        )
        prompt = p.to_system_prompt()
        assert "山田 花子" in prompt
        assert "38歳" in prompt
        assert "関東" in prompt
        assert "既婚・子育て中" in prompt
        assert "スキンケア" in prompt
        assert "肌悩みを減らしたい" in prompt
        # 一人称・生活者向けの表現が含まれる
        assert "生活者" in prompt
        # 医師ドメイン用語の残滓がないこと
        assert "処方" not in prompt
        assert "診療科" not in prompt

    def test_to_skill_md_has_consumer_type(self) -> None:
        p = ConsumerPersona(
            persona_id="t3",
            name="山田 花子",
            age=38,
            gender="female",
            demographics=_make_demo(),
            category_profile=_make_cat(),
        )
        md = p.to_skill_md()
        assert "type: consumer_persona" in md
        assert "physician_persona" not in md

    def test_historical_response_model(self) -> None:
        hr = HistoricalResponse(
            question_text="あなたの普段使っているスキンケア商品は？",
            question_category="skincare",
            response_value="資生堂",
            free_text="品質が安定していて長年使っています",
        )
        assert hr.response_value == "資生堂"
