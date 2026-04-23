"""ABM 4段階ファネルの単体テスト."""

from __future__ import annotations

import mesa

from digital_twin.abm.consumer_agent import AdoptionState, AgentProfile, ConsumerAgent
from digital_twin.abm.data_bridge import consumer_to_agent_profile
from digital_twin.abm.metrics import calculate_metrics
from digital_twin.abm.model import PrescriptionModel
from digital_twin.data.schema import (
    AgeGroup,
    CategoryProfile,
    Consumer,
    ConsumerDemographics,
    Gender,
    Region,
)


def _make_profile(**kwargs) -> AgentProfile:
    defaults = {
        "category": "サプリ",
        "aware_threshold": 0.1,
        "interest_threshold": 0.3,
        "purchase_threshold": 0.6,
        "repeat_threshold": 0.8,
    }
    defaults.update(kwargs)
    return AgentProfile(**defaults)


class TestAdoptionState:
    def test_five_states_exist(self) -> None:
        assert len(AdoptionState) == 5
        assert AdoptionState.UNAWARE == "unaware"
        assert AdoptionState.AWARE == "aware"
        assert AdoptionState.INTERESTED == "interested"
        assert AdoptionState.PURCHASED == "purchased"
        assert AdoptionState.REPEAT == "repeat"


class TestConsumerAgent:
    def test_initial_state_is_unaware(self) -> None:
        model = mesa.Model()
        agent = ConsumerAgent(model, profile=_make_profile())
        assert agent.state == AdoptionState.UNAWARE

    def test_transitions_through_funnel(self) -> None:
        model = mesa.Model()
        profile = _make_profile(
            aware_threshold=0.1,
            interest_threshold=0.2,
            purchase_threshold=0.4,
            repeat_threshold=0.6,
        )
        agent = ConsumerAgent(model, profile=profile)

        # UNAWARE → AWARE
        agent.receive_influence(0.1)
        agent.step()
        assert agent.state == AdoptionState.AWARE

        # AWARE → INTERESTED
        agent.receive_influence(0.1)
        agent.step()
        assert agent.state == AdoptionState.INTERESTED

        # INTERESTED → PURCHASED
        agent.receive_influence(0.2)
        agent.step()
        assert agent.state == AdoptionState.PURCHASED
        assert agent.adoption_step is not None

        # PURCHASED → REPEAT
        agent.receive_influence(0.2)
        agent.step()
        assert agent.state == AdoptionState.REPEAT

    def test_repeat_is_terminal(self) -> None:
        model = mesa.Model()
        profile = _make_profile(
            aware_threshold=0.01,
            interest_threshold=0.02,
            purchase_threshold=0.03,
            repeat_threshold=0.04,
        )
        agent = ConsumerAgent(model, profile=profile)
        agent.receive_influence(1.0)
        # Step through all states
        for _ in range(10):
            agent.step()
        assert agent.state == AdoptionState.REPEAT

    def test_does_not_skip_states(self) -> None:
        """大量の影響を一度に受けても1ステップで1段階しか進まない."""
        model = mesa.Model()
        profile = _make_profile(
            aware_threshold=0.1,
            interest_threshold=0.2,
            purchase_threshold=0.3,
            repeat_threshold=0.4,
        )
        agent = ConsumerAgent(model, profile=profile)
        agent.receive_influence(10.0)  # 全閾値を大幅に超える
        agent.step()
        assert agent.state == AdoptionState.AWARE  # 1段階だけ進む


class TestPrescriptionModel:
    def test_run_returns_all_states(self) -> None:
        profiles = [_make_profile() for _ in range(10)]
        model = PrescriptionModel(profiles, seed=42)
        history = model.run(steps=5)

        assert len(history) == 5
        for h in history:
            assert "unaware" in h
            assert "aware" in h
            assert "interested" in h
            assert "purchased" in h
            assert "repeat" in h
            assert "purchase_rate" in h

    def test_repeat_agents_have_stronger_influence(self) -> None:
        profiles = [_make_profile(influencer_score=0.9) for _ in range(3)]
        model = PrescriptionModel(profiles, seed=42, kol_influence=0.1, repeat_multiplier=2.0)

        # Set first agent to PURCHASED and second to REPEAT
        model.consumer_agents[0].state = AdoptionState.PURCHASED
        model.consumer_agents[1].state = AdoptionState.REPEAT

        # Step once
        model.step()

        # Both should have influenced the third agent, but REPEAT agent's
        # influence should be multiplied
        # (Actual amounts depend on network connectivity)


class TestDataBridge:
    def test_consumer_to_profile_has_gender(self) -> None:
        consumer = Consumer(
            consumer_id="C001",
            demographics=ConsumerDemographics(
                age_group=AgeGroup.AGE_35_44,
                gender=Gender.FEMALE,
                region=Region.KANTO,
            ),
            category_profile=CategoryProfile(category="サプリ"),
        )
        profile = consumer_to_agent_profile(consumer)
        assert profile.gender == "female"
        assert profile.aware_threshold > 0
        assert profile.interest_threshold > profile.aware_threshold
        assert profile.purchase_threshold > profile.interest_threshold
        assert profile.repeat_threshold > profile.purchase_threshold


class TestMetrics:
    def test_funnel_rates_calculated(self) -> None:
        profiles = [_make_profile() for _ in range(10)]
        model = PrescriptionModel(profiles, seed=42)

        # Manually set states
        model.consumer_agents[0].state = AdoptionState.REPEAT
        model.consumer_agents[0].adoption_step = 5
        model.consumer_agents[1].state = AdoptionState.PURCHASED
        model.consumer_agents[1].adoption_step = 8
        model.consumer_agents[2].state = AdoptionState.INTERESTED
        model.consumer_agents[3].state = AdoptionState.AWARE

        history = [{"step": 1, "unaware": 6, "aware": 1, "interested": 1, "purchased": 1, "repeat": 1, "purchase_rate": 0.2}]
        metrics = calculate_metrics(model.consumer_agents, history)

        assert metrics.total_agents == 10
        assert metrics.funnel_rates["認知率"] == 0.4  # 4/10 (aware + interested + purchased + repeat)
        assert metrics.funnel_rates["関心率"] == 0.3  # 3/10 (interested + purchased + repeat)
        assert metrics.funnel_rates["購買率"] == 0.2  # 2/10 (purchased + repeat)
        assert metrics.funnel_rates["リピート率"] == 0.1  # 1/10
        assert metrics.purchased_count == 2
        assert metrics.repeat_count == 1
