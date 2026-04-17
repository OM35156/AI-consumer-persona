"""生活者ペルソナのシミュレーションエンジン.

Two simulation modes:
1. Promotion simulation: persona reacts to a promotion scenario
2. Survey simulation: persona answers a survey
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

from digital_twin.data.schema import PromotionScenario, SurveyInstrument
from digital_twin.engine.prompt import (
    build_promotion_prompt,
    build_promotion_response_schema,
    build_survey_prompt,
    build_survey_response_schema,
)
from digital_twin.persona.profile import ConsumerPersona
from digital_twin.rag.context_builder import ContextBuilder
from digital_twin.rag.search_client import PersonaSearchClient
from digital_twin.utils.cost import CostTracker

logger = logging.getLogger(__name__)


@dataclass
class PromotionSimResult:
    """Result of a promotion response simulation."""
    persona_id: str
    persona_name: str
    scenario_id: str
    responses: dict  # structured response
    model: str
    temperature: float
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    replication_id: int = 0


@dataclass
class SurveySimResult:
    """Result of a survey simulation."""
    persona_id: str
    persona_name: str
    survey_id: str
    responses: dict
    model: str
    temperature: float
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    replication_id: int = 0


@dataclass
class DialogueResult:
    """Result of a freeform dialogue simulation."""

    persona_id: str
    persona_name: str
    query: str
    response_text: str
    confidence_level: str = ""
    evidence_sources: list[str] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


class Simulator:
    """生活者ペルソナシミュレーションエンジン（Claude API）."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.8,
        max_tokens: int = 4096,
        max_concurrent: int = 10,
        search_client: PersonaSearchClient | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_concurrent = max_concurrent
        self.client = anthropic.Anthropic()
        self.async_client = anthropic.AsyncAnthropic()
        self.cost_tracker = CostTracker()
        self._search_client = search_client
        self._context_builder = context_builder

    # --- Promotion Simulation ---

    def simulate_promotion(
        self,
        persona: ConsumerPersona,
        scenario: PromotionScenario,
        replication_id: int = 0,
    ) -> PromotionSimResult:
        """Simulate a persona's response to a promotion scenario."""
        system_prompt, user_prompt = build_promotion_prompt(persona, scenario)
        response_schema = build_promotion_response_schema()

        tool_def = {
            "name": "submit_promotion_response",
            "description": "プロモーションへの反応を送信する",
            "input_schema": response_schema,
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "submit_promotion_response"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        responses = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_promotion_response":
                responses = block.input
                break

        self.cost_tracker.record(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return PromotionSimResult(
            persona_id=persona.persona_id,
            persona_name=persona.name,
            scenario_id=scenario.scenario_id,
            responses=responses,
            model=self.model,
            temperature=self.temperature,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            replication_id=replication_id,
        )

    async def _simulate_promotion_async(
        self,
        persona: ConsumerPersona,
        scenario: PromotionScenario,
        replication_id: int = 0,
    ) -> PromotionSimResult:
        system_prompt, user_prompt = build_promotion_prompt(persona, scenario)
        response_schema = build_promotion_response_schema()

        tool_def = {
            "name": "submit_promotion_response",
            "description": "プロモーションへの反応を送信する",
            "input_schema": response_schema,
        }

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "submit_promotion_response"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        responses = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_promotion_response":
                responses = block.input
                break

        self.cost_tracker.record(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return PromotionSimResult(
            persona_id=persona.persona_id,
            persona_name=persona.name,
            scenario_id=scenario.scenario_id,
            responses=responses,
            model=self.model,
            temperature=self.temperature,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            replication_id=replication_id,
        )

    async def simulate_promotion_batch_async(
        self,
        personas: list[ConsumerPersona],
        scenario: PromotionScenario,
        replications: int = 3,
    ) -> list[PromotionSimResult]:
        """Simulate multiple personas' reactions to a promotion."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _run(persona: ConsumerPersona, rep: int) -> PromotionSimResult:
            async with semaphore:
                logger.info(
                    "Simulating %s (rep=%d) for scenario=%s",
                    persona.name, rep, scenario.scenario_id,
                )
                return await self._simulate_promotion_async(persona, scenario, rep)

        tasks = [
            _run(persona, rep)
            for persona in personas
            for rep in range(replications)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        for e in errors:
            logger.error("Promotion simulation failed: %s", e)

        return valid

    def simulate_promotion_batch(
        self,
        personas: list[ConsumerPersona],
        scenario: PromotionScenario,
        replications: int = 3,
    ) -> list[PromotionSimResult]:
        return asyncio.run(
            self.simulate_promotion_batch_async(personas, scenario, replications)
        )

    # --- Survey Simulation ---

    def simulate_survey(
        self,
        persona: ConsumerPersona,
        survey: SurveyInstrument,
        replication_id: int = 0,
    ) -> SurveySimResult:
        """Simulate a persona's response to a survey."""
        system_prompt, user_prompt = build_survey_prompt(persona, survey)
        response_schema = build_survey_response_schema(survey)

        tool_def = {
            "name": "submit_survey_response",
            "description": "調査回答を送信する",
            "input_schema": response_schema,
        }

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "submit_survey_response"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        responses = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_survey_response":
                responses = block.input
                break

        self.cost_tracker.record(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return SurveySimResult(
            persona_id=persona.persona_id,
            persona_name=persona.name,
            survey_id=survey.survey_id,
            responses=responses,
            model=self.model,
            temperature=self.temperature,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            replication_id=replication_id,
        )

    async def _simulate_survey_async(
        self,
        persona: ConsumerPersona,
        survey: SurveyInstrument,
        replication_id: int = 0,
    ) -> SurveySimResult:
        """非同期 Survey シミュレーション（単一）"""
        system_prompt, user_prompt = build_survey_prompt(persona, survey)
        response_schema = build_survey_response_schema(survey)

        tool_def = {
            "name": "submit_survey_response",
            "description": "調査回答を送信する",
            "input_schema": response_schema,
        }

        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            tools=[tool_def],
            tool_choice={"type": "tool", "name": "submit_survey_response"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        responses = {}
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_survey_response":
                responses = block.input
                break

        self.cost_tracker.record(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return SurveySimResult(
            persona_id=persona.persona_id,
            persona_name=persona.name,
            survey_id=survey.survey_id,
            responses=responses,
            model=self.model,
            temperature=self.temperature,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            replication_id=replication_id,
        )

    async def simulate_survey_batch_async(
        self,
        personas: list[ConsumerPersona],
        survey: SurveyInstrument,
        replications: int = 3,
    ) -> list[SurveySimResult]:
        """複数ペルソナの Survey 回答を非同期バッチ実行する。"""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def _run(persona: ConsumerPersona, rep: int) -> SurveySimResult:
            async with semaphore:
                logger.info(
                    "Simulating %s (rep=%d) for survey=%s",
                    persona.name, rep, survey.survey_id,
                )
                return await self._simulate_survey_async(persona, survey, rep)

        tasks = [
            _run(persona, rep)
            for persona in personas
            for rep in range(replications)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]
        for e in errors:
            logger.error("Survey simulation failed: %s", e)

        return valid

    def simulate_survey_batch(
        self,
        personas: list[ConsumerPersona],
        survey: SurveyInstrument,
        replications: int = 3,
    ) -> list[SurveySimResult]:
        """複数ペルソナの Survey 回答をバッチ実行する（同期ラッパー）。"""
        return asyncio.run(
            self.simulate_survey_batch_async(personas, survey, replications)
        )

    # --- Dialogue Simulation (RAG対応) ---

    def simulate_dialogue(
        self,
        persona: ConsumerPersona,
        query: str,
        segment: dict | None = None,
        product: str | None = None,
        query_vector: list[float] | None = None,
    ) -> DialogueResult:
        """自由対話シミュレーション（RAG コンテキスト付き）."""
        # RAG コンテキスト構築
        rag_context = ""
        evidence_sources: list[str] = []
        confidence = ""

        if self._context_builder and query_vector and segment:
            results = self._context_builder.search_context(
                query_vector=query_vector,
                segment=segment,
                product=product,
            )
            if results:
                rag_context = self._context_builder.build_context_text(
                    segment=segment, search_results=results,
                )
                evidence_sources = [r.metadata.get("source", "") for r in results]
                from digital_twin.rag.context_builder import confidence_label
                avg_score = sum(r.score for r in results) / len(results)
                confidence = confidence_label(avg_score)

        system_prompt = persona.to_system_prompt(rag_context=rag_context or None)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": query}],
        )

        response_text = response.content[0].text if response.content else ""

        self.cost_tracker.record(
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return DialogueResult(
            persona_id=persona.persona_id,
            persona_name=persona.name,
            query=query,
            response_text=response_text,
            confidence_level=confidence,
            evidence_sources=evidence_sources,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def get_cost_summary(self) -> dict:
        return self.cost_tracker.summary()
