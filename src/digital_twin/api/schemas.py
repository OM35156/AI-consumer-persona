"""API リクエスト/レスポンスのスキーマ定義。"""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- ヘルスチェック ---


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


# --- ペルソナ ---


class PersonaSummary(BaseModel):
    """ペルソナ一覧用の要約モデル。"""
    persona_id: str
    name: str
    age: int
    gender: str
    specialty: str
    facility_type: str
    catchphrase: str = ""


class PersonaDetail(PersonaSummary):
    """ペルソナ詳細モデル。"""
    goals: list[str] = []
    factoids: list[str] = []
    personality_traits: list[str] = []
    system_prompt: str = ""


# --- シミュレーション ---


class PromotionSimRequest(BaseModel):
    """プロモーションシミュレーションリクエスト。"""
    persona_ids: list[str] = Field(..., description="対象ペルソナIDリスト")
    scenario_id: str = Field(..., description="プロモーションシナリオID")
    replications: int = Field(default=3, ge=1, le=10)


class SurveySimRequest(BaseModel):
    """サーベイシミュレーションリクエスト。"""
    persona_ids: list[str] = Field(..., description="対象ペルソナIDリスト")
    survey_id: str = Field(..., description="サーベイID")
    replications: int = Field(default=3, ge=1, le=10)


class SimResultItem(BaseModel):
    """シミュレーション結果の個別アイテム。"""
    persona_id: str
    persona_name: str
    replication_id: int
    responses: dict
    input_tokens: int = 0
    output_tokens: int = 0


class SimResponse(BaseModel):
    """シミュレーション結果のレスポンス。"""
    results: list[SimResultItem]
    total_count: int
    cost_summary: dict


# --- バリデーション ---


class ValidateRequest(BaseModel):
    """バリデーションリクエスト。"""
    survey_id: str = Field(..., description="検証用サーベイID")
    js_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    mode_threshold: float = Field(default=0.70, ge=0.0, le=1.0)


class MetricItem(BaseModel):
    """メトリクス結果。"""
    name: str
    value: float
    threshold: float
    passed: bool
    details: str = ""


class ValidateResponse(BaseModel):
    """バリデーション結果のレスポンス。"""
    overall_pass: bool
    pass_rate: float
    n_questions: int
    n_respondents: int
    metrics: list[MetricItem]
