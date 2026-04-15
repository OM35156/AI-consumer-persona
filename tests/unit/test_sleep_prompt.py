"""engine/sleep_prompt.py の単体テスト."""

from __future__ import annotations

import pytest

from digital_twin.data.schema import (
    AgeGroup,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    ExerciseFrequency,
    Gender,
    LifeStage,
    Region,
    SleepConcern,
    SleepProduct,
    SleepProfile,
)
from digital_twin.engine.sleep_prompt import (
    load_template,
    render_sleep_interview_prompt,
)


def _build_consumer(
    concerns: list[SleepConcern] | None = None,
    products: list[SleepProduct] | None = None,
) -> Consumer:
    return Consumer(
        consumer_id="TEST_SP_001",
        demographics=ConsumerDemographics(
            age_group=AgeGroup.AGE_35_44,
            gender=Gender.FEMALE,
            region=Region.KANTO,
            life_stage=LifeStage.MARRIED_WITH_CHILDREN,
            occupation="会社員",
            household_income="600-800万円",
        ),
        category_profile=CategoryProfile(
            category="睡眠関連商品",
            purchase_philosophy="質の良いものを長く使いたい",
            price_sensitivity="moderate",
            new_product_receptivity="late",
        ),
        sleep_profile=SleepProfile(
            avg_sleep_duration_hours=6.0,
            bedtime="23:30",
            wake_time="06:00",
            sleep_quality_5=2,
            concerns=concerns if concerns is not None else [SleepConcern.MIDNIGHT_AWAKENING],
            product_usage=products if products is not None else [SleepProduct.PILLOW],
            caffeine_intake_per_day=2,
            exercise_frequency=ExerciseFrequency.RARE,
            stress_level_5=4,
            chronotype="intermediate",
        ),
    )


class TestLoadTemplate:
    def test_load_returns_nonempty_string(self) -> None:
        tmpl = load_template()
        assert "Role" in tmpl
        assert "{{persona_name}}" in tmpl
        assert "{{concerns_ja}}" in tmpl


class TestRender:
    def test_basic_rendering(self) -> None:
        c = _build_consumer()
        prompt = render_sleep_interview_prompt(
            consumer=c,
            persona_name="山田 花子",
            age=38,
            question="寝つきが悪いときはどうしていますか？",
        )
        # 属性が埋め込まれている
        assert "山田 花子" in prompt
        assert "38歳" in prompt
        assert "女性" in prompt
        assert "関東" in prompt
        assert "既婚・子育て中" in prompt
        assert "会社員" in prompt
        # 睡眠プロファイル
        assert "6.0 時間" in prompt
        assert "23:30" in prompt
        assert "中途覚醒" in prompt
        assert "枕" in prompt
        # 質問が埋め込まれている
        assert "寝つきが悪いときはどうしていますか？" in prompt
        # 医師ドメイン語が含まれない
        assert "処方" not in prompt or "処方薬" in prompt  # SleepProduct.PRESCRIPTION の「処方薬」はOK
        assert "診療科" not in prompt
        # テンプレート未置換が残っていない
        assert "{{" not in prompt
        assert "}}" not in prompt

    def test_rendering_with_no_concerns(self) -> None:
        c = _build_consumer(concerns=[SleepConcern.NONE], products=[])
        prompt = render_sleep_interview_prompt(
            consumer=c, persona_name="田中 太郎", age=38, question="最近の睡眠はどうですか？"
        )
        assert "特になし" in prompt
        assert "特に使っていない" in prompt

    def test_rendering_with_multiple_concerns(self) -> None:
        c = _build_consumer(
            concerns=[
                SleepConcern.MIDNIGHT_AWAKENING,
                SleepConcern.SHORT_DURATION,
                SleepConcern.DAYTIME_SLEEPINESS,
            ],
            products=[SleepProduct.SUPPLEMENT, SleepProduct.AROMA],
        )
        prompt = render_sleep_interview_prompt(
            consumer=c, persona_name="X", age=38, question="Q"
        )
        assert "中途覚醒" in prompt
        assert "睡眠時間不足" in prompt
        assert "日中の眠気" in prompt
        assert "サプリ" in prompt
        assert "アロマ" in prompt

    def test_raises_when_sleep_profile_missing(self) -> None:
        c = Consumer(
            consumer_id="NO_SLEEP",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_25_34,
                gender=Gender.MALE,
                region=Region.KANTO,
            ),
            category_profile=CategoryProfile(category="睡眠関連商品"),
        )
        with pytest.raises(ValueError, match="sleep_profile"):
            render_sleep_interview_prompt(
                consumer=c, persona_name="X", age=30, question="Q"
            )

    def test_custom_template(self) -> None:
        c = _build_consumer()
        tmpl = "名前={{persona_name}} 年齢={{age}} 悩み={{concern_summary}} 質問={{question}}"
        prompt = render_sleep_interview_prompt(
            consumer=c, persona_name="山田", age=38, question="よく眠れますか？",
            template=tmpl,
        )
        assert prompt.startswith("名前=山田")
        assert "年齢=38" in prompt
        assert "悩み=中途覚醒" in prompt
        assert "質問=よく眠れますか？" in prompt
