"""Prompt construction for physician persona simulation.

Two main simulation modes:
1. Promotion Response: Present promotion scenario → get prescription intent
2. Survey Response: Present survey questions → get structured answers

Both use the persona's system prompt (from profile.py) as grounding.
"""

from __future__ import annotations

import json

from digital_twin.data.schema import (
    PromotionScenario,
    QuestionType,
    SurveyInstrument,
)
from digital_twin.persona.profile import PhysicianPersona

# --- Mode 1: Promotion Response Simulation ---


PROMOTION_PROMPT_TEMPLATE = """\
以下のプロモーションを受けました。あなた（{name}）として、率直に反応してください。

## プロモーション情報
- 製薬企業: {pharma_company}
- 製品名: {product_name}
- 疾患領域: {therapeutic_area}
- チャネル: {channel}
- 新薬: {is_new_drug_ja}

### キーメッセージ
{key_message}

{detail_section}
{clinical_data_section}

## 回答してください

以下のJSON形式で、あなたの反応を返してください。
一人称で、あなたの処方哲学・日常・性格に基づいた具体的な反応をしてください。

```json
{{
  "prescription_intent": "increase / maintain / decrease / start / no_intent のいずれか",
  "intent_reason": "処方意向の理由（1-2文）",
  "message_evaluation": "キーメッセージへの評価（+2:喜ぶ / +1:役立つ / 0:無関心 / -1:困惑する）",
  "message_feedback": "キーメッセージへの具体的な一人称コメント",
  "channel_fit": "このチャネルが自分に合っているか（1-5, 5が最適）",
  "information_needs": "追加で知りたい情報",
  "walkthrough": "このプロモーションを受けている場面を一人称で描写（2-3文）"
}}
```"""


def build_promotion_prompt(
    persona: PhysicianPersona,
    scenario: PromotionScenario,
) -> tuple[str, str]:
    """Build system + user prompt for promotion response simulation.

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = persona.to_system_prompt()

    # Add promotion history context
    history = persona.get_promotion_history_summary()
    if history:
        system_prompt += "\n\n" + history

    # Add few-shot examples
    few_shot = persona.get_few_shot_examples()
    if few_shot:
        system_prompt += "\n\n" + few_shot

    detail_section = ""
    if scenario.detail_content:
        detail_section = f"\n### ディテール内容\n{scenario.detail_content}"

    clinical_data_section = ""
    if scenario.clinical_data_summary:
        clinical_data_section = f"\n### 臨床データ\n{scenario.clinical_data_summary}"

    from digital_twin.persona.profile import _channel_ja
    channel_name = _channel_ja(scenario.channel.value)

    user_prompt = PROMOTION_PROMPT_TEMPLATE.format(
        name=persona.name,
        pharma_company=scenario.pharma_company,
        product_name=scenario.product_name,
        therapeutic_area=scenario.therapeutic_area,
        channel=channel_name,
        is_new_drug_ja="はい" if scenario.is_new_drug else "いいえ",
        key_message=scenario.key_message,
        detail_section=detail_section,
        clinical_data_section=clinical_data_section,
    )

    return system_prompt, user_prompt


def build_promotion_response_schema() -> dict:
    """JSON schema for structured promotion response."""
    return {
        "type": "object",
        "properties": {
            "prescription_intent": {
                "type": "string",
                "enum": ["increase", "maintain", "decrease", "start", "no_intent"],
                "description": "今後の処方意向",
            },
            "intent_reason": {
                "type": "string",
                "description": "処方意向の理由（一人称で）",
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
            "prescription_intent",
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
対象疾患: {target_disease}

{questions_block}

【回答形式】
以下のJSON形式で回答してください。各設問IDをキーとし、回答を値としてください。
自由回答の場合は、あなたが実際に書くであろう文章で、一人称で回答してください。
複数回答の場合はリスト形式で返してください。

回答例:
{example_json}
"""


def build_survey_prompt(
    persona: PhysicianPersona,
    survey: SurveyInstrument,
) -> tuple[str, str]:
    """Build system + user prompt for survey response simulation.

    Returns:
        (system_prompt, user_prompt)
    """
    system_prompt = persona.to_system_prompt()

    history = persona.get_promotion_history_summary()
    if history:
        system_prompt += "\n\n" + history

    few_shot = persona.get_few_shot_examples()
    if few_shot:
        system_prompt += "\n\n" + few_shot

    user_prompt = _build_survey_user_prompt(persona.name, survey)

    return system_prompt, user_prompt


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
        target_disease=survey.target_disease or "一般",
        questions_block=questions_block,
        example_json=example_json,
    )


def build_survey_response_schema(survey: SurveyInstrument) -> dict:
    """Build JSON schema for structured survey output."""
    properties = {}
    required = []

    for q in survey.questions:
        required.append(q.question_id)

        if q.question_type == QuestionType.SINGLE_CHOICE and q.options:
            properties[q.question_id] = {
                "type": "string",
                "enum": q.options,
                "description": q.question_text,
            }
        elif q.question_type == QuestionType.MULTIPLE_CHOICE and q.options:
            properties[q.question_id] = {
                "type": "array",
                "items": {"type": "string", "enum": q.options},
                "description": q.question_text,
            }
        elif q.question_type in (QuestionType.LIKERT_5, QuestionType.LIKERT_7) and q.options:
            properties[q.question_id] = {
                "type": "string",
                "enum": q.options,
                "description": q.question_text,
            }
        elif q.question_type == QuestionType.NUMERIC:
            properties[q.question_id] = {
                "type": "number",
                "description": q.question_text,
            }
        elif q.question_type == QuestionType.FREE_TEXT:
            properties[q.question_id] = {
                "type": "string",
                "description": q.question_text,
            }

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
