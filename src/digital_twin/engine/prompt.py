"""生活者ペルソナシミュレーション用のプロンプト構築.

Two main simulation modes:
1. Promotion Response: プロモーション提示 → 購買意向を取得
2. Survey Response: 調査設問提示 → 構造化された回答を取得

Both use the persona's system prompt (from profile.py) as grounding.
"""

from __future__ import annotations

import json

from digital_twin.data.schema import (
    PromotionScenario,
    QuestionType,
    SurveyInstrument,
)
from digital_twin.persona.profile import ConsumerPersona, _channel_ja

# --- Mode 1: Promotion Response Simulation ---


PROMOTION_PROMPT_TEMPLATE = """\
以下のプロモーションを受けました。あなた（{name}）として、率直に反応してください。

## プロモーション情報
- ブランド名: {brand_name}
- カテゴリ: {category}
- チャネル: {channel}
- 新商品: {is_new_product_ja}
- ターゲット: {target_audience}

### キーメッセージ
{key_message}

{detail_section}

## 回答してください

以下のJSON形式で、あなたの反応を返してください。
一人称で、あなたの購買哲学・日常・性格に基づいた具体的な反応をしてください。

```json
{{
  "purchase_intent": "definitely_buy / probably_buy / might_buy / probably_not / definitely_not のいずれか",
  "intent_reason": "購買意向の理由（1-2文）",
  "message_evaluation": "キーメッセージへの評価（+2:喜ぶ / +1:役立つ / 0:無関心 / -1:困惑する）",
  "message_feedback": "キーメッセージへの具体的な一人称コメント",
  "channel_fit": "このチャネルが自分に合っているか（1-5, 5が最適）",
  "information_needs": "追加で知りたい情報",
  "walkthrough": "このプロモーションを受けている場面を一人称で描写（2-3文）"
}}
```"""


def build_promotion_prompt(
    persona: ConsumerPersona,
    scenario: PromotionScenario,
) -> tuple[str, str]:
    """プロモーション反応シミュレーション用のプロンプトを構築する.

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = persona.to_system_prompt()

    # ブランド接触履歴コンテキストを追加
    history = persona.get_brand_history_summary()
    if history:
        system_prompt += "\n\n" + history

    # few-shot 例を追加
    few_shot = persona.get_few_shot_examples()
    if few_shot:
        system_prompt += "\n\n" + few_shot

    detail_section = ""
    if scenario.detail_content:
        detail_section = f"\n### 詳細内容\n{scenario.detail_content}"

    channel_name = _channel_ja(scenario.channel.value)

    user_prompt = PROMOTION_PROMPT_TEMPLATE.format(
        name=persona.name,
        brand_name=scenario.brand_name,
        category=scenario.category,
        channel=channel_name,
        is_new_product_ja="はい" if scenario.is_new_product else "いいえ",
        target_audience=scenario.target_audience or "一般",
        key_message=scenario.key_message,
        detail_section=detail_section,
    )

    return system_prompt, user_prompt


def build_promotion_response_schema() -> dict:
    """プロモーション反応の JSON スキーマ."""
    return {
        "type": "object",
        "properties": {
            "purchase_intent": {
                "type": "string",
                "enum": [
                    "definitely_buy", "probably_buy", "might_buy",
                    "probably_not", "definitely_not",
                ],
                "description": "今後の購買意向",
            },
            "intent_reason": {
                "type": "string",
                "description": "購買意向の理由（一人称で）",
            },
            "message_evaluation": {
                "type": "integer",
                "enum": [-1, 0, 1, 2],
                "description": "キーメッセージ評価: +2=喜ぶ, +1=役立つ, 0=無関心, -1=困惑",
            },
            "message_feedback": {
                "type": "string",
                "description": "キーメッセージへの具体的コメント（一人称）",
            },
            "channel_fit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
                "description": "チャネル適合度 1-5",
            },
            "information_needs": {
                "type": "string",
                "description": "追加で知りたい情報",
            },
            "walkthrough": {
                "type": "string",
                "description": "プロモーション場面の一人称描写",
            },
        },
        "required": [
            "purchase_intent",
            "intent_reason",
            "message_evaluation",
            "message_feedback",
            "channel_fit",
            "information_needs",
            "walkthrough",
        ],
    }


# --- Mode 2: Survey Response Simulation ---


SURVEY_PROMPT_TEMPLATE = """\
以下の調査に、あなた（{name}）として回答してください。

調査名: {survey_name}
対象カテゴリ: {target_category}

{questions_block}

【回答形式】
以下のJSON形式で回答してください。各設問IDをキーとし、回答を値としてください。
自由回答の場合は、あなたが実際に書くであろう文章で、一人称で回答してください。
複数回答の場合はリスト形式で返してください。

回答例:
{example_json}
"""


def build_survey_prompt(
    persona: ConsumerPersona,
    survey: SurveyInstrument,
) -> tuple[str, str]:
    """調査回答シミュレーション用のプロンプトを構築する.

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = persona.to_system_prompt()

    history = persona.get_brand_history_summary()
    if history:
        system_prompt += "\n\n" + history

    few_shot = persona.get_few_shot_examples()
    if few_shot:
        system_prompt += "\n\n" + few_shot

    user_prompt = _build_survey_user_prompt(persona.name, survey)

    return system_prompt, user_prompt


def build_survey_response_schema(survey: SurveyInstrument) -> dict:
    """調査回答の JSON スキーマを構築する."""
    properties = {}
    required = []

    for q in survey.questions:
        prop: dict = {}
        if q.question_type in (QuestionType.SINGLE_CHOICE, QuestionType.FREE_TEXT):
            prop = {"type": "string"}
        elif q.question_type == QuestionType.MULTIPLE_CHOICE:
            prop = {"type": "array", "items": {"type": "string"}}
        elif q.question_type in (QuestionType.LIKERT_5, QuestionType.LIKERT_7, QuestionType.NUMERIC):
            prop = {"type": "number"}
        else:
            prop = {"type": "string"}

        prop["description"] = q.question_text
        properties[q.question_id] = prop
        required.append(q.question_id)

    return {"type": "object", "properties": properties, "required": required}


def _build_survey_user_prompt(name: str, survey: SurveyInstrument) -> str:
    questions_lines = []
    example_response = {}

    for q in survey.questions:
        line = f"### {q.question_id}: {q.question_text}"
        if q.question_type == QuestionType.SINGLE_CHOICE and q.options:
            line += f"\n選択肢: {' / '.join(q.options)}"
            example_response[q.question_id] = q.options[0]
        elif q.question_type == QuestionType.MULTIPLE_CHOICE and q.options:
            line += f"\n選択肢（複数回答可）: {' / '.join(q.options)}"
            example_response[q.question_id] = [q.options[0]]
        elif q.question_type in (QuestionType.LIKERT_5, QuestionType.LIKERT_7) and q.options:
            line += f"\n尺度: {' / '.join(q.options)}"
            example_response[q.question_id] = q.options[2]
        elif q.question_type == QuestionType.NUMERIC:
            line += "\n数値で回答してください"
            example_response[q.question_id] = 0
        elif q.question_type == QuestionType.FREE_TEXT:
            line += "\n一人称で自由にお書きください"
            example_response[q.question_id] = "回答テキスト"

        questions_lines.append(line)

    questions_block = "\n\n".join(questions_lines)
    example_json = json.dumps(example_response, ensure_ascii=False, indent=2)

    return SURVEY_PROMPT_TEMPLATE.format(
        name=name,
        survey_name=survey.survey_name,
        target_category=survey.target_category or "一般",
        questions_block=questions_block,
        example_json=example_json,
    )
