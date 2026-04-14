"""Pydantic data models for consumer persona / lifestyle data.

生活者 AI ペルソナ用のデータモデル定義。
医師版（AI-persona）から汎用化し、消費者行動・購買意向・
情報接触チャネルのシミュレーションに対応する。
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AgeGroup(str, Enum):
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_64 = "55-64"
    AGE_65_PLUS = "65+"


class Region(str, Enum):
    HOKKAIDO = "hokkaido"
    TOHOKU = "tohoku"
    KANTO = "kanto"
    CHUBU = "chubu"
    KINKI = "kinki"
    CHUGOKU = "chugoku"
    SHIKOKU = "shikoku"
    KYUSHU = "kyushu"


class LifeStage(str, Enum):
    """ライフステージ."""
    STUDENT = "student"
    SINGLE_WORKING = "single_working"
    MARRIED_NO_CHILDREN = "married_no_children"
    MARRIED_WITH_CHILDREN = "married_with_children"
    EMPTY_NEST = "empty_nest"
    RETIRED = "retired"


class InformationChannel(str, Enum):
    """情報接触チャネル."""
    TV_CM = "tv_cm"
    WEB_AD = "web_ad"
    SNS = "sns"
    WORD_OF_MOUTH = "word_of_mouth"
    STORE_DISPLAY = "store_display"
    MAGAZINE = "magazine"
    INFLUENCER = "influencer"
    SEARCH_ENGINE = "search_engine"
    EC_SITE = "ec_site"


class PurchaseIntent(str, Enum):
    """購買意向."""
    DEFINITELY_BUY = "definitely_buy"
    PROBABLY_BUY = "probably_buy"
    MIGHT_BUY = "might_buy"
    PROBABLY_NOT = "probably_not"
    DEFINITELY_NOT = "definitely_not"


class BrandAwareness(str, Enum):
    """ブランド認知状態."""
    ACTIVE_USER = "active_user"
    PAST_USER = "past_user"
    AWARE_NOT_USED = "aware_not_used"
    UNAWARE = "unaware"


class ScaleUsagePattern(str, Enum):
    """回答スタイル傾向."""
    EXTREME = "extreme"
    MODERATE = "moderate"
    ACQUIESCENT = "acquiescent"
    BALANCED = "balanced"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    LIKERT_5 = "likert_5"
    LIKERT_7 = "likert_7"
    FREE_TEXT = "free_text"
    NUMERIC = "numeric"


# --- Consumer Profile ---


class ConsumerDemographics(BaseModel):
    """生活者属性情報."""
    age_group: AgeGroup
    gender: Gender
    region: Region
    life_stage: LifeStage = LifeStage.SINGLE_WORKING
    occupation: str = ""
    household_income: str = ""
    is_influencer: bool = False


class CategoryProfile(BaseModel):
    """カテゴリ購買プロファイル."""
    category: str  # 商品カテゴリ（例：スキンケア、健康食品）
    primary_brands: list[str] = []
    brand_status: dict[str, BrandAwareness] = {}
    purchase_philosophy: str = ""
    price_sensitivity: str = "moderate"  # high / moderate / low
    new_product_receptivity: str = "moderate"  # early / moderate / late


class ChannelPreference(BaseModel):
    """情報チャネル嗜好性."""
    channel: InformationChannel
    receptivity: int = Field(default=3, ge=1, le=5)
    frequency_per_month: int = Field(default=0, ge=0)
    preferred: bool = False


class BrandExposure(BaseModel):
    """ブランド接触記録."""
    date: date
    channel: InformationChannel
    brand_name: str
    category: str = ""
    content_summary: str = ""
    current_awareness: BrandAwareness = BrandAwareness.AWARE_NOT_USED
    purchase_intent_after: PurchaseIntent = PurchaseIntent.MIGHT_BUY


class ResponseStyle(BaseModel):
    """回答スタイル特性."""
    scale_usage: ScaleUsagePattern = ScaleUsagePattern.BALANCED
    free_text_verbosity: str = "medium"
    consistency_score: float = Field(default=0.8, ge=0.0, le=1.0)
    survey_receptivity: str = "moderate"


# --- Persona Components ---


class PersonaGoal(BaseModel):
    """ペルソナのゴール."""
    goal_type: str  # "health" / "beauty" / "lifestyle" / "savings"
    description: str
    priority: int = Field(default=3, ge=1, le=5)


class Factoid(BaseModel):
    """ファクトイド."""
    category: str
    content: str
    data_source: str = ""


class PersonalityTrait(BaseModel):
    """心理的詳細."""
    trait_name: str
    description: str


# --- Survey ---


class SurveyQuestion(BaseModel):
    """調査設問定義."""
    question_id: str
    question_text: str
    question_type: QuestionType
    options: Optional[list[str]] = None
    category: str = ""


class PromotionScenario(BaseModel):
    """プロモーションシナリオ."""
    scenario_id: str
    brand_name: str
    category: str
    channel: InformationChannel
    key_message: str
    detail_content: str = ""
    target_audience: str = ""
    is_new_product: bool = False


class SurveyInstrument(BaseModel):
    """調査票全体の定義."""
    survey_id: str
    survey_name: str
    description: str = ""
    questions: list[SurveyQuestion]
    target_category: str = ""
    survey_date: Optional[date] = None
    promotion_scenarios: list[PromotionScenario] = []


class QuestionResponse(BaseModel):
    """個別設問への回答."""
    question_id: str
    response_value: str | int | float | list[str] | None = None
    free_text: Optional[str] = None


class SurveyResponse(BaseModel):
    """1生活者の調査回答全体."""
    respondent_id: str
    survey_id: str
    responses: list[QuestionResponse]
    completion_date: Optional[date] = None


# --- Consumer (Raw Data Record) ---


class Consumer(BaseModel):
    """生活者の全データ."""
    consumer_id: str
    demographics: ConsumerDemographics
    category_profile: CategoryProfile
    channel_preferences: list[ChannelPreference] = []
    brand_history: list[BrandExposure] = []
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)
    survey_responses: list[SurveyResponse] = []
    goals: list[PersonaGoal] = []
    factoids: list[Factoid] = []
    personality_traits: list[PersonalityTrait] = []
