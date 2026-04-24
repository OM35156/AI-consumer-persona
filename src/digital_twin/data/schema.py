"""Pydantic data models for consumer persona / lifestyle data.

生活者 AI ペルソナ用のデータモデル定義。
医師版（AI-persona）から汎用化し、消費者行動・購買意向・
情報接触チャネルのシミュレーションに対応する。
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

# --- Enums ---


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class AgeGroup(StrEnum):
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_64 = "55-64"
    AGE_65_PLUS = "65+"


class Region(StrEnum):
    HOKKAIDO = "hokkaido"
    TOHOKU = "tohoku"
    KANTO = "kanto"
    CHUBU = "chubu"
    KINKI = "kinki"
    CHUGOKU = "chugoku"
    SHIKOKU = "shikoku"
    KYUSHU = "kyushu"


class LifeStage(StrEnum):
    """ライフステージ."""
    STUDENT = "student"
    SINGLE_WORKING = "single_working"
    MARRIED_NO_CHILDREN = "married_no_children"
    MARRIED_WITH_CHILDREN = "married_with_children"
    EMPTY_NEST = "empty_nest"
    RETIRED = "retired"


class InformationChannel(StrEnum):
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


class PurchaseIntent(StrEnum):
    """購買意向."""
    DEFINITELY_BUY = "definitely_buy"
    PROBABLY_BUY = "probably_buy"
    MIGHT_BUY = "might_buy"
    PROBABLY_NOT = "probably_not"
    DEFINITELY_NOT = "definitely_not"


class BrandAwareness(StrEnum):
    """ブランド認知状態."""
    ACTIVE_USER = "active_user"
    PAST_USER = "past_user"
    AWARE_NOT_USED = "aware_not_used"
    UNAWARE = "unaware"


class ScaleUsagePattern(StrEnum):
    """回答スタイル傾向."""
    EXTREME = "extreme"
    MODERATE = "moderate"
    ACQUIESCENT = "acquiescent"
    BALANCED = "balanced"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    LIKERT_5 = "likert_5"
    LIKERT_7 = "likert_7"
    FREE_TEXT = "free_text"
    NUMERIC = "numeric"


# --- Sleep Domain Enums ---


class SleepConcern(StrEnum):
    """睡眠の悩み."""
    DIFFICULTY_FALLING_ASLEEP = "difficulty_falling_asleep"  # 入眠困難
    MIDNIGHT_AWAKENING = "midnight_awakening"                # 中途覚醒
    EARLY_AWAKENING = "early_awakening"                      # 早朝覚醒
    POOR_QUALITY = "poor_quality"                            # 熟眠感不足
    SHORT_DURATION = "short_duration"                        # 睡眠時間不足
    DAYTIME_SLEEPINESS = "daytime_sleepiness"                # 日中の眠気
    NONE = "none"


class SleepProduct(StrEnum):
    """利用している睡眠関連商品."""
    SUPPLEMENT = "supplement"        # サプリ
    MATTRESS = "mattress"            # マットレス
    PILLOW = "pillow"                # 枕
    PAJAMAS = "pajamas"              # パジャマ
    AROMA = "aroma"                  # アロマ
    APP = "app"                      # 睡眠アプリ
    PRESCRIPTION = "prescription"    # 処方薬


class ExerciseFrequency(StrEnum):
    """運動頻度."""
    DAILY = "daily"
    WEEKLY = "weekly"
    RARE = "rare"
    NONE = "none"


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
    options: list[str] | None = None
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
    survey_date: date | None = None
    promotion_scenarios: list[PromotionScenario] = []


class QuestionResponse(BaseModel):
    """個別設問への回答."""
    question_id: str
    response_value: str | int | float | list[str] | None = None
    free_text: str | None = None


class SurveyResponse(BaseModel):
    """1生活者の調査回答全体."""
    respondent_id: str
    survey_id: str
    responses: list[QuestionResponse]
    completion_date: date | None = None


# --- Sleep Profile ---


class SleepProfile(BaseModel):
    """睡眠プロファイル."""

    avg_sleep_duration_hours: float = Field(default=7.0, ge=0.0, le=24.0)
    bedtime: str = "23:30"                                      # 就寝時刻 "HH:MM"
    wake_time: str = "06:30"                                    # 起床時刻 "HH:MM"
    sleep_quality_5: int = Field(default=3, ge=1, le=5)         # 主観的睡眠満足度（5段階）
    concerns: list[SleepConcern] = []
    product_usage: list[SleepProduct] = []
    caffeine_intake_per_day: int = Field(default=0, ge=0)       # 1日のカフェイン摂取回数
    exercise_frequency: ExerciseFrequency = ExerciseFrequency.RARE
    stress_level_5: int = Field(default=3, ge=1, le=5)          # 主観的ストレスレベル
    chronotype: str = "intermediate"                            # morning / intermediate / evening


# --- Consumer (Raw Data Record) ---


# --- External Panel Data ---


class MonthlyPurchaseRecord(BaseModel):
    """SCI 月次購入レコード."""

    consumer_id: str
    month: str  # "2025-01" 形式
    category: str
    brand: str = ""
    is_new_purchase: bool = False
    is_repeat_purchase: bool = False
    quantity: int = Field(default=1, ge=0)
    amount_yen: int = Field(default=0, ge=0)


class StoreSalesRecord(BaseModel):
    """SRI 店舗POS集計レコード."""

    region: Region
    channel: str  # 流通チャネル（例: "ドラッグストア", "コンビニ", "EC"）
    category: str
    brand: str = ""
    month: str  # "2025-01" 形式
    sales_volume: int = Field(default=0, ge=0)
    sales_amount_yen: int = Field(default=0, ge=0)
    purchase_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class WebActionType(StrEnum):
    """i-SSP ウェブ行動の種別."""

    PAGE_VIEW = "page_view"
    SEARCH = "search"
    AD_IMPRESSION = "ad_impression"
    AD_CLICK = "ad_click"
    EC_VISIT = "ec_visit"
    REVIEW_READ = "review_read"
    SNS_VIEW = "sns_view"


class WebBehaviorLog(BaseModel):
    """i-SSP ウェブ行動ログレコード."""

    consumer_id: str
    timestamp: str  # "2025-01-15T10:30:00" 形式
    action_type: WebActionType
    url: str = ""
    domain: str = ""
    page_title: str = ""
    duration_seconds: int = Field(default=0, ge=0)
    search_keyword: str = ""
    ad_campaign_id: str = ""
    related_brand: str = ""
    related_category: str = ""


class DigitalJourney(BaseModel):
    """i-SSP セッション単位の行動経路."""

    consumer_id: str
    session_id: str
    session_date: date
    logs: list[WebBehaviorLog] = []
    resulted_in_purchase: bool = False
    purchased_brand: str = ""


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
    sleep_profile: SleepProfile | None = None
