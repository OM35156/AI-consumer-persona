"""FastAPI アプリケーション定義。"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from digital_twin import __version__
from digital_twin.api.schemas import (
    HealthResponse,
    MetricItem,
    PersonaDetail,
    PersonaSummary,
    PromotionSimRequest,
    SimResponse,
    SimResultItem,
    SurveySimRequest,
    ValidateRequest,
    ValidateResponse,
)
from digital_twin.api.state import AppState

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Digital Twin API",
    description="医師AIペルソナ シミュレーション API",
    version=__version__,
)
state = AppState()


@app.on_event("startup")
async def startup() -> None:
    """アプリ起動時にデータとペルソナを読み込む。"""
    state.initialize()
    logger.info("App started: %d personas loaded", len(state.personas))


# --- ヘルスチェック ---


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__)


# --- ペルソナ ---


@app.get("/api/personas", response_model=list[PersonaSummary])
async def list_personas() -> list[PersonaSummary]:
    """ペルソナ一覧を返す。"""
    return [
        PersonaSummary(
            persona_id=p.persona_id,
            name=p.name,
            age=p.age,
            gender=p.gender,
            specialty=p.specialty,
            facility_type=p.facility_type,
            catchphrase=p.catchphrase,
        )
        for p in state.personas
    ]


@app.get("/api/personas/{persona_id}", response_model=PersonaDetail)
async def get_persona(persona_id: str) -> PersonaDetail:
    """ペルソナ詳細を返す。"""
    p = state.get_persona(persona_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Persona {persona_id} not found")
    return PersonaDetail(
        persona_id=p.persona_id,
        name=p.name,
        age=p.age,
        gender=p.gender,
        specialty=p.specialty,
        facility_type=p.facility_type,
        catchphrase=p.catchphrase,
        goals=[g.description for g in p.goals],
        factoids=[f.text for f in p.factoids],
        personality_traits=[t.trait_name for t in p.personality_traits],
        system_prompt=p.to_system_prompt(),
    )


# --- プロモーションシミュレーション ---


@app.post("/api/simulate/promotion", response_model=SimResponse)
async def simulate_promotion(req: PromotionSimRequest) -> SimResponse:
    """プロモーション反応をシミュレーションする。"""
    personas = [state.get_persona(pid) for pid in req.persona_ids]
    if any(p is None for p in personas):
        missing = [pid for pid, p in zip(req.persona_ids, personas, strict=True) if p is None]
        raise HTTPException(status_code=404, detail=f"Personas not found: {missing}")

    scenario = state.get_scenario(req.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {req.scenario_id} not found")

    sim_results = await state.simulator.simulate_promotion_batch_async(
        personas=personas,
        scenario=scenario,
        replications=req.replications,
    )

    items = [
        SimResultItem(
            persona_id=r.persona_id,
            persona_name=r.persona_name,
            replication_id=r.replication_id,
            responses=r.responses,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
        )
        for r in sim_results
    ]

    return SimResponse(
        results=items,
        total_count=len(items),
        cost_summary=state.simulator.get_cost_summary(),
    )


# --- サーベイシミュレーション ---


@app.post("/api/simulate/survey", response_model=SimResponse)
async def simulate_survey(req: SurveySimRequest) -> SimResponse:
    """サーベイ回答をシミュレーションする。"""
    personas = [state.get_persona(pid) for pid in req.persona_ids]
    if any(p is None for p in personas):
        missing = [pid for pid, p in zip(req.persona_ids, personas, strict=True) if p is None]
        raise HTTPException(status_code=404, detail=f"Personas not found: {missing}")

    survey = state.get_survey(req.survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail=f"Survey {req.survey_id} not found")

    sim_results = await state.simulator.simulate_survey_batch_async(
        personas=personas,
        survey=survey,
        replications=req.replications,
    )

    items = [
        SimResultItem(
            persona_id=r.persona_id,
            persona_name=r.persona_name,
            replication_id=r.replication_id,
            responses=r.responses,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
        )
        for r in sim_results
    ]

    return SimResponse(
        results=items,
        total_count=len(items),
        cost_summary=state.simulator.get_cost_summary(),
    )


# --- バリデーション ---


@app.post("/api/validate", response_model=ValidateResponse)
async def validate_results(req: ValidateRequest) -> ValidateResponse:
    """ホールドアウトデータに対するバリデーションを実行する。"""
    from digital_twin.evaluation.validator import validate

    if not state.holdout_consumers:
        raise HTTPException(status_code=400, detail="No holdout data available")

    survey = state.get_survey(req.survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail=f"Survey {req.survey_id} not found")

    # ホールドアウトのペルソナでシミュレーション実行
    holdout_personas = [
        state.get_persona(c.consumer_id)
        for c in state.holdout_consumers
    ]
    holdout_personas = [p for p in holdout_personas if p is not None]

    if not holdout_personas:
        raise HTTPException(status_code=400, detail="No holdout personas available")

    sim_results = await state.simulator.simulate_survey_batch_async(
        personas=holdout_personas,
        survey=survey,
        replications=1,
    )

    report = validate(
        real_respondents=state.holdout_consumers,
        simulation_results=sim_results,
        validation_survey_id=req.survey_id,
        js_threshold=req.js_threshold,
        mode_threshold=req.mode_threshold,
    )

    return ValidateResponse(
        overall_pass=report.overall_pass,
        pass_rate=report.pass_rate,
        n_questions=report.n_questions,
        n_respondents=report.n_respondents,
        metrics=[
            MetricItem(
                name=m.name,
                value=m.value,
                threshold=m.threshold,
                passed=m.passed,
                details=m.details,
            )
            for m in report.metrics
        ],
    )
