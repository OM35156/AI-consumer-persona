"""アプリケーション状態管理.

起動時にデータとペルソナを読み込み、エンドポイントから参照する。
"""

from __future__ import annotations

import logging

from digital_twin.data.anonymizer import anonymize_dataset
from digital_twin.data.loader import load_dataset, split_holdout
from digital_twin.data.schema import Consumer, PromotionScenario, SurveyInstrument
from digital_twin.engine.simulator import Simulator
from digital_twin.persona.builder import ConsumerPersonaBuilder
from digital_twin.persona.profile import ConsumerPersona
from digital_twin.utils.config import load_config

logger = logging.getLogger(__name__)


class AppState:
    """API のグローバル状態."""

    def __init__(self) -> None:
        self.personas: list[ConsumerPersona] = []
        self.scenarios: list[PromotionScenario] = []
        self.surveys: list[SurveyInstrument] = []
        self.holdout_consumers: list[Consumer] = []
        self.simulator: Simulator = Simulator()
        self._persona_map: dict[str, ConsumerPersona] = {}
        self._scenario_map: dict[str, PromotionScenario] = {}
        self._survey_map: dict[str, SurveyInstrument] = {}

    def initialize(self, config_profile: str = "poc") -> None:
        """データ読込・匿名化・ペルソナ構築を行う."""
        config = load_config(config_profile)

        # データ読込
        consumers, surveys, scenarios = load_dataset(
            config.data.get("raw_dir", "./data/dummy")
        )
        logger.info(
            "Loaded %d consumers, %d surveys, %d scenarios",
            len(consumers), len(surveys), len(scenarios),
        )

        # 匿名化
        anon_config = config.get("anonymization", {})
        consumers, _ = anonymize_dataset(
            consumers,
            k=anon_config.get("k_anonymity", 5),
        )

        # ホールドアウト分割
        holdout_ratio = config.get("evaluation", {}).get("holdout_ratio", 0.3)
        train, holdout = split_holdout(consumers, holdout_ratio=holdout_ratio)
        self.holdout_consumers = holdout

        # ペルソナ構築
        builder = ConsumerPersonaBuilder()
        self.personas = builder.build_batch(train)
        self._persona_map = {p.persona_id: p for p in self.personas}

        # シナリオ・サーベイ
        self.scenarios = scenarios
        self._scenario_map = {s.scenario_id: s for s in scenarios}
        self.surveys = surveys
        self._survey_map = {s.survey_id: s for s in surveys}

        # シミュレータ設定
        llm_config = config.get("llm", {})
        self.simulator = Simulator(
            model=llm_config.get("default_model", "claude-sonnet-4-20250514"),
            temperature=llm_config.get("temperature", 0.8),
            max_tokens=llm_config.get("max_tokens", 4096),
        )

    def get_persona(self, persona_id: str) -> ConsumerPersona | None:
        return self._persona_map.get(persona_id)

    def get_scenario(self, scenario_id: str) -> PromotionScenario | None:
        return self._scenario_map.get(scenario_id)

    def get_survey(self, survey_id: str) -> SurveyInstrument | None:
        return self._survey_map.get(survey_id)
