"""schema.py の Pydantic モデルと Enum 定義の単体テスト."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from digital_twin.data.schema import (
    AgeGroup,
    BrandAwareness,
    BrandExposure,
    CategoryProfile,
    ChannelPreference,
    Consumer,
    ConsumerDemographics,
    ExerciseFrequency,
    Gender,
    InformationChannel,
    LifeStage,
    PurchaseIntent,
    Region,
    ResponseStyle,
    ScaleUsagePattern,
    SleepConcern,
    SleepProduct,
    SleepProfile,
)


class TestEnums:
    """Enum の値一覧・値の互換性を検証する."""

    def test_age_group_values(self) -> None:
        # 生活者版の年代層（医師版の 30-39..70+ とは異なる）
        assert AgeGroup.AGE_18_24.value == "18-24"
        assert AgeGroup.AGE_25_34.value == "25-34"
        assert AgeGroup.AGE_65_PLUS.value == "65+"
        assert len(list(AgeGroup)) == 6

    def test_life_stage_values(self) -> None:
        expected = {
            "student", "single_working", "married_no_children",
            "married_with_children", "empty_nest", "retired",
        }
        assert {ls.value for ls in LifeStage} == expected

    def test_information_channel_values(self) -> None:
        # 生活者チャネル（TV/Web広告/SNS/口コミ等）
        assert InformationChannel.TV_CM.value == "tv_cm"
        assert InformationChannel.SNS.value == "sns"
        assert InformationChannel.EC_SITE.value == "ec_site"
        assert "mr_detail" not in {c.value for c in InformationChannel}  # 医師版の残滓なし

    def test_purchase_intent_values(self) -> None:
        assert PurchaseIntent.DEFINITELY_BUY.value == "definitely_buy"
        assert PurchaseIntent.DEFINITELY_NOT.value == "definitely_not"

    def test_brand_awareness_values(self) -> None:
        expected = {"active_user", "past_user", "aware_not_used", "unaware"}
        assert {ba.value for ba in BrandAwareness} == expected

    def test_scale_usage_pattern_values(self) -> None:
        expected = {"extreme", "moderate", "acquiescent", "balanced"}
        assert {sp.value for sp in ScaleUsagePattern} == expected


class TestConsumerDemographics:
    """ConsumerDemographics のバリデーション."""

    def test_build_minimal(self) -> None:
        demo = ConsumerDemographics(
            age_group=AgeGroup.AGE_35_44,
            gender=Gender.FEMALE,
            region=Region.KANTO,
        )
        assert demo.age_group == AgeGroup.AGE_35_44
        # デフォルト値の確認
        assert demo.life_stage == LifeStage.SINGLE_WORKING
        assert demo.occupation == ""
        assert demo.is_influencer is False

    def test_missing_required_raises(self) -> None:
        with pytest.raises(ValidationError):
            ConsumerDemographics()  # type: ignore[call-arg]

    def test_invalid_enum_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            ConsumerDemographics(
                age_group="invalid",  # type: ignore[arg-type]
                gender=Gender.FEMALE,
                region=Region.KANTO,
            )


class TestBrandExposure:
    """BrandExposure のバリデーション."""

    def test_build_with_required_fields(self) -> None:
        exp = BrandExposure(
            date=date(2026, 4, 1),
            channel=InformationChannel.SNS,
            brand_name="Test Brand",
        )
        assert exp.brand_name == "Test Brand"
        # デフォルト値
        assert exp.current_awareness == BrandAwareness.AWARE_NOT_USED
        assert exp.purchase_intent_after == PurchaseIntent.MIGHT_BUY

    def test_full_build(self) -> None:
        exp = BrandExposure(
            date=date(2026, 4, 1),
            channel=InformationChannel.TV_CM,
            brand_name="資生堂",
            category="スキンケア",
            content_summary="新CM放映",
            current_awareness=BrandAwareness.ACTIVE_USER,
            purchase_intent_after=PurchaseIntent.PROBABLY_BUY,
        )
        assert exp.category == "スキンケア"
        assert exp.current_awareness == BrandAwareness.ACTIVE_USER


class TestChannelPreference:
    """ChannelPreference のバリデーション（receptivity 1-5 制約）."""

    def test_receptivity_in_range(self) -> None:
        cp = ChannelPreference(channel=InformationChannel.SNS, receptivity=4)
        assert cp.receptivity == 4

    def test_receptivity_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            ChannelPreference(channel=InformationChannel.SNS, receptivity=6)
        with pytest.raises(ValidationError):
            ChannelPreference(channel=InformationChannel.SNS, receptivity=0)


class TestConsumer:
    """Consumer トップレベルモデル."""

    def test_build_with_required_fields(self) -> None:
        consumer = Consumer(
            consumer_id="C001",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_25_34,
                gender=Gender.MALE,
                region=Region.KINKI,
            ),
            category_profile=CategoryProfile(category="サプリ"),
        )
        assert consumer.consumer_id == "C001"
        assert consumer.brand_history == []  # default
        assert isinstance(consumer.response_style, ResponseStyle)

    def test_roundtrip_serialization(self) -> None:
        consumer = Consumer(
            consumer_id="C002",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_45_54,
                gender=Gender.FEMALE,
                region=Region.KANTO,
                life_stage=LifeStage.MARRIED_WITH_CHILDREN,
            ),
            category_profile=CategoryProfile(
                category="スキンケア",
                price_sensitivity="low",
            ),
        )
        dumped = consumer.model_dump_json()
        restored = Consumer.model_validate_json(dumped)
        assert restored == consumer


class TestSleepProfile:
    """SleepProfile のバリデーション."""

    def test_build_default(self) -> None:
        sp = SleepProfile()
        assert sp.avg_sleep_duration_hours == 7.0
        assert sp.bedtime == "23:30"
        assert sp.sleep_quality_5 == 3
        assert sp.concerns == []
        assert sp.exercise_frequency == ExerciseFrequency.RARE
        assert sp.chronotype == "intermediate"

    def test_build_with_concerns(self) -> None:
        sp = SleepProfile(
            avg_sleep_duration_hours=5.5,
            concerns=[SleepConcern.MIDNIGHT_AWAKENING, SleepConcern.POOR_QUALITY],
            product_usage=[SleepProduct.PILLOW, SleepProduct.AROMA],
            caffeine_intake_per_day=3,
            exercise_frequency=ExerciseFrequency.WEEKLY,
            stress_level_5=4,
        )
        assert SleepConcern.MIDNIGHT_AWAKENING in sp.concerns
        assert sp.caffeine_intake_per_day == 3
        assert sp.stress_level_5 == 4

    def test_sleep_quality_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            SleepProfile(sleep_quality_5=6)
        with pytest.raises(ValidationError):
            SleepProfile(sleep_quality_5=0)

    def test_duration_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            SleepProfile(avg_sleep_duration_hours=-1.0)
        with pytest.raises(ValidationError):
            SleepProfile(avg_sleep_duration_hours=25.0)

    def test_caffeine_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SleepProfile(caffeine_intake_per_day=-1)


class TestConsumerWithSleep:
    """Consumer に SleepProfile を統合できること."""

    def test_sleep_profile_default_none(self) -> None:
        consumer = Consumer(
            consumer_id="C100",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE,
                region=Region.KANTO,
            ),
            category_profile=CategoryProfile(category="寝具"),
        )
        assert consumer.sleep_profile is None

    def test_with_sleep_profile_roundtrip(self) -> None:
        consumer = Consumer(
            consumer_id="C101",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE,
                region=Region.KANTO,
                life_stage=LifeStage.MARRIED_WITH_CHILDREN,
            ),
            category_profile=CategoryProfile(category="寝具"),
            sleep_profile=SleepProfile(
                avg_sleep_duration_hours=6.0,
                concerns=[SleepConcern.MIDNIGHT_AWAKENING],
                product_usage=[SleepProduct.PILLOW],
                sleep_quality_5=2,
                stress_level_5=4,
            ),
        )
        dumped = consumer.model_dump_json()
        restored = Consumer.model_validate_json(dumped)
        assert restored == consumer
        assert restored.sleep_profile is not None
        assert SleepConcern.MIDNIGHT_AWAKENING in restored.sleep_profile.concerns
