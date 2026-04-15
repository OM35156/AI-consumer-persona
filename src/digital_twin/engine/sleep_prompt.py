"""睡眠インタビュー用プロンプトのロードとレンダリング.

templates/sleep_interview.md を読み込み、Consumer（+ SleepProfile）の
属性を埋め込んだ system prompt 文字列を返す。

注: engine/prompt.py は medical 版の依存を残しているため、本モジュールは
独立した小さなユーティリティとして実装する。UI スタックの全面整理時に
統合・一元化を検討する。
"""

from __future__ import annotations

from pathlib import Path

from digital_twin.data.schema import (
    Consumer,
    ExerciseFrequency,
    Gender,
    LifeStage,
    Region,
    SleepConcern,
    SleepProduct,
)

_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "sleep_interview.md"


# --- 日本語変換ヘルパー ---


def _gender_ja(g: Gender) -> str:
    return {Gender.MALE: "男性", Gender.FEMALE: "女性", Gender.OTHER: "その他"}.get(g, str(g))


def _region_ja(r: Region) -> str:
    return {
        Region.HOKKAIDO: "北海道",
        Region.TOHOKU: "東北",
        Region.KANTO: "関東",
        Region.CHUBU: "中部",
        Region.KINKI: "近畿",
        Region.CHUGOKU: "中国",
        Region.SHIKOKU: "四国",
        Region.KYUSHU: "九州",
    }.get(r, str(r))


def _life_stage_ja(ls: LifeStage) -> str:
    return {
        LifeStage.STUDENT: "学生",
        LifeStage.SINGLE_WORKING: "独身・勤労",
        LifeStage.MARRIED_NO_CHILDREN: "既婚・子なし",
        LifeStage.MARRIED_WITH_CHILDREN: "既婚・子育て中",
        LifeStage.EMPTY_NEST: "子独立後",
        LifeStage.RETIRED: "退職後",
    }.get(ls, str(ls))


def _concern_ja(c: SleepConcern) -> str:
    return {
        SleepConcern.DIFFICULTY_FALLING_ASLEEP: "入眠困難",
        SleepConcern.MIDNIGHT_AWAKENING: "中途覚醒",
        SleepConcern.EARLY_AWAKENING: "早朝覚醒",
        SleepConcern.POOR_QUALITY: "熟眠感不足",
        SleepConcern.SHORT_DURATION: "睡眠時間不足",
        SleepConcern.DAYTIME_SLEEPINESS: "日中の眠気",
        SleepConcern.NONE: "特になし",
    }.get(c, str(c))


def _product_ja(p: SleepProduct) -> str:
    return {
        SleepProduct.SUPPLEMENT: "サプリ",
        SleepProduct.MATTRESS: "マットレス",
        SleepProduct.PILLOW: "枕",
        SleepProduct.PAJAMAS: "パジャマ",
        SleepProduct.AROMA: "アロマ",
        SleepProduct.APP: "睡眠アプリ",
        SleepProduct.PRESCRIPTION: "処方薬",
    }.get(p, str(p))


def _exercise_ja(ef: ExerciseFrequency) -> str:
    return {
        ExerciseFrequency.DAILY: "ほぼ毎日",
        ExerciseFrequency.WEEKLY: "週に数回",
        ExerciseFrequency.RARE: "たまに",
        ExerciseFrequency.NONE: "していない",
    }.get(ef, str(ef))


_CHRONOTYPE_JA = {
    "morning": "朝型",
    "intermediate": "中間型",
    "evening": "夜型",
}


_PRICE_JA = {"high": "価格にシビア", "moderate": "標準的", "low": "品質重視"}
_RECV_JA = {"early": "新商品に積極的", "moderate": "標準的", "late": "慎重派"}


# --- テンプレート読込 & レンダリング ---


def load_template(path: Path | None = None) -> str:
    """テンプレートファイルを読み込んで文字列で返す."""
    return (path or _TEMPLATE_PATH).read_text(encoding="utf-8")


def render_sleep_interview_prompt(
    consumer: Consumer,
    persona_name: str,
    age: int,
    question: str,
    template: str | None = None,
) -> str:
    """Consumer + 質問から睡眠インタビュー用 system prompt を生成する.

    Args:
        consumer: 生活者データ（sleep_profile が設定されていること）
        persona_name: 表示用ペルソナ名
        age: 代表年齢
        question: ユーザーの質問
        template: テンプレート文字列（省略時は templates/sleep_interview.md をロード）

    Raises:
        ValueError: consumer.sleep_profile が None の場合
    """
    if consumer.sleep_profile is None:
        raise ValueError("consumer.sleep_profile が未設定です")

    sp = consumer.sleep_profile
    demo = consumer.demographics
    cat = consumer.category_profile

    tmpl = template if template is not None else load_template()

    # 悩み一覧 → 箇条書き
    if sp.concerns and sp.concerns != [SleepConcern.NONE]:
        concerns_ja = "\n".join(
            f"- {_concern_ja(c)}" for c in sp.concerns if c != SleepConcern.NONE
        )
        concern_summary = "・".join(
            _concern_ja(c) for c in sp.concerns if c != SleepConcern.NONE
        )
    else:
        concerns_ja = "- 特になし"
        concern_summary = "特になし"

    # 利用商品一覧
    if sp.product_usage:
        products_ja = "\n".join(f"- {_product_ja(p)}" for p in sp.product_usage)
    else:
        products_ja = "- 特に使っていない"

    replacements = {
        "{{persona_name}}": persona_name,
        "{{age}}": str(age),
        "{{gender_ja}}": _gender_ja(demo.gender),
        "{{region_ja}}": _region_ja(demo.region),
        "{{life_stage_ja}}": _life_stage_ja(demo.life_stage),
        "{{occupation}}": demo.occupation or "未設定",
        "{{avg_sleep_duration_hours}}": f"{sp.avg_sleep_duration_hours:.1f}",
        "{{bedtime}}": sp.bedtime,
        "{{wake_time}}": sp.wake_time,
        "{{sleep_quality_5}}": str(sp.sleep_quality_5),
        "{{chronotype_ja}}": _CHRONOTYPE_JA.get(sp.chronotype, sp.chronotype),
        "{{concerns_ja}}": concerns_ja,
        "{{concern_summary}}": concern_summary,
        "{{product_usage_ja}}": products_ja,
        "{{caffeine_intake_per_day}}": str(sp.caffeine_intake_per_day),
        "{{exercise_frequency_ja}}": _exercise_ja(sp.exercise_frequency),
        "{{stress_level_5}}": str(sp.stress_level_5),
        "{{purchase_philosophy}}": cat.purchase_philosophy or "未設定",
        "{{price_sensitivity_ja}}": _PRICE_JA.get(cat.price_sensitivity, cat.price_sensitivity),
        "{{new_product_receptivity_ja}}": _RECV_JA.get(
            cat.new_product_receptivity, cat.new_product_receptivity
        ),
        "{{question}}": question,
    }

    rendered = tmpl
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)

    return rendered
