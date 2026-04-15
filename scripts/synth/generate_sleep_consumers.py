"""睡眠ペルソナ PoC 用のサンプル合成データ生成スクリプト.

年代 × 性別 × ライフステージの人口分布に従って Consumer を生成し、
各人に SleepProfile を付与する。睡眠悩みの分布は年代・ライフステージと
相関を持つ（例: 育児期女性は中途覚醒率↑、高齢層は早朝覚醒率↑）。

使い方:
    uv run python scripts/synth/generate_sleep_consumers.py --n 300 --seed 42 \\
        --out data/synthetic/sleep_consumers_v1.json
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from digital_twin.data.schema import (
    AgeGroup,
    BrandAwareness,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    ExerciseFrequency,
    Gender,
    LifeStage,
    Region,
    ResponseStyle,
    ScaleUsagePattern,
    SleepConcern,
    SleepProduct,
    SleepProfile,
)

# --- 人口分布（日本の簡易近似、合計が 1.0 になるよう正規化） ---

_AGE_WEIGHTS = {
    AgeGroup.AGE_18_24: 0.10,
    AgeGroup.AGE_25_34: 0.17,
    AgeGroup.AGE_35_44: 0.20,
    AgeGroup.AGE_45_54: 0.22,
    AgeGroup.AGE_55_64: 0.16,
    AgeGroup.AGE_65_PLUS: 0.15,
}

_REGION_WEIGHTS = {
    Region.HOKKAIDO: 0.04,
    Region.TOHOKU: 0.07,
    Region.KANTO: 0.34,
    Region.CHUBU: 0.17,
    Region.KINKI: 0.18,
    Region.CHUGOKU: 0.06,
    Region.SHIKOKU: 0.03,
    Region.KYUSHU: 0.11,
}

# 年代 → よくあるライフステージ分布
_LIFE_STAGE_BY_AGE: dict[AgeGroup, dict[LifeStage, float]] = {
    AgeGroup.AGE_18_24: {LifeStage.STUDENT: 0.55, LifeStage.SINGLE_WORKING: 0.45},
    AgeGroup.AGE_25_34: {
        LifeStage.SINGLE_WORKING: 0.45,
        LifeStage.MARRIED_NO_CHILDREN: 0.20,
        LifeStage.MARRIED_WITH_CHILDREN: 0.35,
    },
    AgeGroup.AGE_35_44: {
        LifeStage.SINGLE_WORKING: 0.15,
        LifeStage.MARRIED_NO_CHILDREN: 0.10,
        LifeStage.MARRIED_WITH_CHILDREN: 0.75,
    },
    AgeGroup.AGE_45_54: {
        LifeStage.SINGLE_WORKING: 0.15,
        LifeStage.MARRIED_WITH_CHILDREN: 0.65,
        LifeStage.EMPTY_NEST: 0.20,
    },
    AgeGroup.AGE_55_64: {
        LifeStage.MARRIED_WITH_CHILDREN: 0.25,
        LifeStage.EMPTY_NEST: 0.55,
        LifeStage.RETIRED: 0.20,
    },
    AgeGroup.AGE_65_PLUS: {
        LifeStage.EMPTY_NEST: 0.30,
        LifeStage.RETIRED: 0.70,
    },
}

# 世帯年収の簡易分布
_INCOME_BRACKETS = [
    "200万円未満", "200-400万円", "400-600万円", "600-800万円",
    "800-1000万円", "1000万円以上",
]
_INCOME_WEIGHTS = [0.10, 0.25, 0.25, 0.20, 0.12, 0.08]

# 職業候補（ライフステージ別）
_OCCUPATIONS = {
    LifeStage.STUDENT: ["学生"],
    LifeStage.SINGLE_WORKING: ["会社員", "公務員", "専門職", "自営業", "フリーランス"],
    LifeStage.MARRIED_NO_CHILDREN: ["会社員", "公務員", "専門職", "パート"],
    LifeStage.MARRIED_WITH_CHILDREN: ["会社員", "専業主婦/主夫", "パート", "自営業"],
    LifeStage.EMPTY_NEST: ["会社員", "パート", "専業主婦/主夫"],
    LifeStage.RETIRED: ["退職", "嘱託", "パート"],
}


def _pick_weighted(rng: random.Random, weights: dict):
    """辞書型の重み付き選択."""
    items = list(weights.keys())
    w = list(weights.values())
    return rng.choices(items, weights=w, k=1)[0]


def _sleep_profile_for(
    rng: random.Random,
    age: AgeGroup,
    gender: Gender,
    life_stage: LifeStage,
) -> SleepProfile:
    """年代/性別/ライフステージに相関する睡眠プロファイルを生成する."""
    # ベース睡眠時間: 年代が上がるにつれて短く
    base_hours_by_age = {
        AgeGroup.AGE_18_24: 7.3,
        AgeGroup.AGE_25_34: 6.9,
        AgeGroup.AGE_35_44: 6.6,
        AgeGroup.AGE_45_54: 6.5,
        AgeGroup.AGE_55_64: 6.7,
        AgeGroup.AGE_65_PLUS: 6.4,
    }
    hours = max(4.0, min(10.0, rng.gauss(base_hours_by_age[age], 0.8)))

    # 就寝・起床時刻（簡易）
    bedtime_hour = rng.choice(["22:30", "23:00", "23:30", "00:00", "00:30", "01:00"])
    wake_hour = rng.choice(["05:30", "06:00", "06:30", "07:00", "07:30"])

    # 睡眠悩みの確率（年代・ライフステージで調整）
    concerns: list[SleepConcern] = []
    prob = {c: 0.08 for c in SleepConcern if c != SleepConcern.NONE}

    # 20代は入眠困難が多い
    if age in (AgeGroup.AGE_18_24, AgeGroup.AGE_25_34):
        prob[SleepConcern.DIFFICULTY_FALLING_ASLEEP] = 0.30
        prob[SleepConcern.DAYTIME_SLEEPINESS] = 0.25
    # 育児期は中途覚醒が多い（女性は特に）
    if life_stage == LifeStage.MARRIED_WITH_CHILDREN:
        prob[SleepConcern.MIDNIGHT_AWAKENING] = 0.45 if gender == Gender.FEMALE else 0.25
        prob[SleepConcern.SHORT_DURATION] = 0.35
    # 更年期（45-54 女性）は入眠・中途覚醒増
    if age == AgeGroup.AGE_45_54 and gender == Gender.FEMALE:
        prob[SleepConcern.MIDNIGHT_AWAKENING] = 0.38
        prob[SleepConcern.POOR_QUALITY] = 0.32
    # 高齢者は早朝覚醒率が高い
    if age in (AgeGroup.AGE_55_64, AgeGroup.AGE_65_PLUS):
        prob[SleepConcern.EARLY_AWAKENING] = 0.40
        prob[SleepConcern.POOR_QUALITY] = 0.25

    for c, p in prob.items():
        if rng.random() < p:
            concerns.append(c)
    if not concerns:
        concerns = [SleepConcern.NONE]

    # 睡眠商品（悩みがあるほど利用率高）
    products: list[SleepProduct] = []
    if SleepConcern.NONE not in concerns:
        product_candidates = list(SleepProduct)
        for p in product_candidates:
            if rng.random() < 0.12:
                products.append(p)

    # 満足度: 悩み数と逆相関
    n_concerns = len([c for c in concerns if c != SleepConcern.NONE])
    base_quality = 5 - min(n_concerns, 3)
    quality = max(1, min(5, int(round(rng.gauss(base_quality, 0.6)))))

    # ストレスレベル: 睡眠満足度と逆相関
    stress = max(1, min(5, 6 - quality + int(round(rng.gauss(0, 0.7)))))

    # 運動頻度
    ex_freq = rng.choices(
        [ExerciseFrequency.DAILY, ExerciseFrequency.WEEKLY,
         ExerciseFrequency.RARE, ExerciseFrequency.NONE],
        weights=[0.12, 0.28, 0.45, 0.15], k=1,
    )[0]

    # カフェイン（年代の高い人ほど多め、例外あり）
    caffeine = rng.choices([0, 1, 2, 3, 4, 5], weights=[0.15, 0.30, 0.30, 0.15, 0.07, 0.03], k=1)[0]

    # chronotype（朝型/夜型）
    chronotype = rng.choices(
        ["morning", "intermediate", "evening"],
        weights=[0.30, 0.50, 0.20], k=1,
    )[0]

    return SleepProfile(
        avg_sleep_duration_hours=round(hours, 1),
        bedtime=bedtime_hour,
        wake_time=wake_hour,
        sleep_quality_5=quality,
        concerns=concerns,
        product_usage=products,
        caffeine_intake_per_day=caffeine,
        exercise_frequency=ex_freq,
        stress_level_5=stress,
        chronotype=chronotype,
    )


def _category_profile_for_sleep(rng: random.Random) -> CategoryProfile:
    """睡眠商品カテゴリのプロファイルを生成する."""
    brands = rng.sample(["ブランドA", "ブランドB", "ブランドC", "ブランドD"], k=rng.randint(1, 3))
    brand_status = {
        b: rng.choice([
            BrandAwareness.ACTIVE_USER, BrandAwareness.PAST_USER,
            BrandAwareness.AWARE_NOT_USED, BrandAwareness.UNAWARE,
        ])
        for b in brands
    }
    return CategoryProfile(
        category="睡眠関連商品",
        primary_brands=brands,
        brand_status=brand_status,
        purchase_philosophy=rng.choice([
            "質の良いものを長く使いたい",
            "手頃な価格で十分な効果があれば満足",
            "新しいものは口コミを見てから試す",
            "自分の体質に合うものを慎重に選ぶ",
        ]),
        price_sensitivity=rng.choice(["high", "moderate", "low"]),
        new_product_receptivity=rng.choice(["early", "moderate", "late"]),
    )


def _response_style(rng: random.Random) -> ResponseStyle:
    return ResponseStyle(
        scale_usage=rng.choice(list(ScaleUsagePattern)),
        free_text_verbosity=rng.choice(["low", "medium", "high"]),
        consistency_score=round(rng.uniform(0.6, 0.95), 2),
        survey_receptivity=rng.choice(["low", "moderate", "high"]),
    )


def _consumer(rng: random.Random, idx: int) -> Consumer:
    age = _pick_weighted(rng, _AGE_WEIGHTS)
    gender = rng.choices([Gender.MALE, Gender.FEMALE, Gender.OTHER], weights=[0.49, 0.49, 0.02], k=1)[0]
    region = _pick_weighted(rng, _REGION_WEIGHTS)
    life_stage = _pick_weighted(rng, _LIFE_STAGE_BY_AGE[age])
    occupation = rng.choice(_OCCUPATIONS[life_stage])
    income = rng.choices(_INCOME_BRACKETS, weights=_INCOME_WEIGHTS, k=1)[0]
    is_influencer = rng.random() < 0.08

    demo = ConsumerDemographics(
        age_group=age,
        gender=gender,
        region=region,
        life_stage=life_stage,
        occupation=occupation,
        household_income=income,
        is_influencer=is_influencer,
    )

    return Consumer(
        consumer_id=f"SYNTH_{idx:05d}",
        demographics=demo,
        category_profile=_category_profile_for_sleep(rng),
        response_style=_response_style(rng),
        sleep_profile=_sleep_profile_for(rng, age, gender, life_stage),
    )


def generate(n: int, seed: int) -> list[Consumer]:
    """N 人分の合成 Consumer を生成する."""
    rng = random.Random(seed)
    return [_consumer(rng, i) for i in range(n)]


def main() -> None:
    parser = argparse.ArgumentParser(description="睡眠ペルソナ用合成データ生成")
    parser.add_argument("--n", type=int, default=300, help="生成する Consumer 数")
    parser.add_argument("--seed", type=int, default=42, help="乱数シード")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/synthetic/sleep_consumers_v1.json"),
        help="出力 JSON パス",
    )
    args = parser.parse_args()

    consumers = generate(args.n, args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = [c.model_dump(mode="json") for c in consumers]
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


    # 簡易統計サマリ
    concern_counts: dict[str, int] = {}
    for c in consumers:
        if c.sleep_profile is None:
            continue
        for concern in c.sleep_profile.concerns:
            concern_counts[concern.value] = concern_counts.get(concern.value, 0) + 1

    for _k, _v in sorted(concern_counts.items(), key=lambda x: -x[1]):
        pass


if __name__ == "__main__":
    main()
