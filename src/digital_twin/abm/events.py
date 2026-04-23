"""外部イベント注入機構 — 学会・ガイドライン改訂・MRキャンペーン等.

設計書 W9 Day2-3 に対応。ABM シミュレーションに任意のタイムステップで
外部イベントを注入し、エージェントの状態を変化させる。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from digital_twin.abm.consumer_agent import ConsumerAgent

logger = logging.getLogger(__name__)


class EventType(StrEnum):
    """外部イベントの種類."""

    CONFERENCE = "conference"  # 学会発表
    GUIDELINE_REVISION = "guideline_revision"  # ガイドライン改訂
    MR_CAMPAIGN = "mr_campaign"  # MRキャンペーン
    SAFETY_ALERT = "safety_alert"  # 安全性アラート


@dataclass
class ABMEvent:
    """ABM に注入する外部イベント."""

    event_type: EventType
    name: str = ""
    target_categories: list[str] = field(default_factory=list)  # 空=全セグメント
    impact_magnitude: float = 0.1  # 影響の大きさ（0-1）
    start_step: int = 1
    duration_steps: int = 3


# デフォルトインパクト係数（config で上書き可能）
DEFAULT_CONFERENCE_KOL_MULTIPLIER = 0.5
DEFAULT_CONFERENCE_GENERAL_MULTIPLIER = 0.2
DEFAULT_GUIDELINE_THRESHOLD_FACTOR = 0.3
DEFAULT_MR_CAMPAIGN_FACTOR = 0.3
DEFAULT_SAFETY_ALERT_FACTOR = 0.5


def apply_conference(
    agents: list[ConsumerAgent],
    event: ABMEvent,
    kol_multiplier: float = DEFAULT_CONFERENCE_KOL_MULTIPLIER,
    general_multiplier: float = DEFAULT_CONFERENCE_GENERAL_MULTIPLIER,
) -> int:
    """学会イベント: KOL の影響力を一時ブーストする."""
    affected = 0
    for agent in agents:
        if event.target_categories and agent.profile.category not in event.target_categories:
            continue
        if agent.is_influencer:
            agent.receive_influence(event.impact_magnitude * kol_multiplier)
        else:
            agent.receive_influence(event.impact_magnitude * general_multiplier)
        affected += 1
    return affected


def apply_guideline_revision(
    agents: list[ConsumerAgent],
    event: ABMEvent,
    threshold_factor: float = DEFAULT_GUIDELINE_THRESHOLD_FACTOR,
) -> int:
    """ガイドライン改訂: 対象セグメントの採用閾値をシフトする."""
    affected = 0
    for agent in agents:
        if event.target_categories and agent.profile.category not in event.target_categories:
            continue
        agent.profile.purchase_threshold = max(
            0.05,
            agent.profile.purchase_threshold - event.impact_magnitude * threshold_factor,
        )
        affected += 1
    return affected


def apply_mr_campaign(
    agents: list[ConsumerAgent],
    event: ABMEvent,
    impact_factor: float = DEFAULT_MR_CAMPAIGN_FACTOR,
) -> int:
    """MRキャンペーン: 接触による影響を増加させる."""
    affected = 0
    for agent in agents:
        if event.target_categories and agent.profile.category not in event.target_categories:
            continue
        agent.receive_influence(event.impact_magnitude * impact_factor)
        affected += 1
    return affected


def apply_safety_alert(
    agents: list[ConsumerAgent],
    event: ABMEvent,
    reduction_factor: float = DEFAULT_SAFETY_ALERT_FACTOR,
) -> int:
    """安全性アラート: 採用にネガティブ影響（影響度を減少）."""
    affected = 0
    for agent in agents:
        if event.target_categories and agent.profile.category not in event.target_categories:
            continue
        agent.influence_accumulated = max(
            0.0,
            agent.influence_accumulated - event.impact_magnitude * reduction_factor,
        )
        affected += 1
    return affected


_EVENT_HANDLERS = {
    EventType.CONFERENCE: apply_conference,
    EventType.GUIDELINE_REVISION: apply_guideline_revision,
    EventType.MR_CAMPAIGN: apply_mr_campaign,
    EventType.SAFETY_ALERT: apply_safety_alert,
}


class EventScheduler:
    """イベントをスケジュールし、適切なタイムステップで適用する."""

    def __init__(self) -> None:
        self._events: list[ABMEvent] = []

    def add_event(self, event: ABMEvent) -> None:
        """イベントを追加する."""
        self._events.append(event)

    def get_active_events(self, step: int) -> list[ABMEvent]:
        """現在のステップでアクティブなイベントを返す."""
        return [
            e for e in self._events
            if e.start_step <= step < e.start_step + e.duration_steps
        ]

    def apply_events(self, step: int, agents: list[ConsumerAgent]) -> list[tuple[ABMEvent, int]]:
        """現在のステップのイベントを全て適用し、(event, affected_count) を返す."""
        results = []
        for event in self.get_active_events(step):
            handler = _EVENT_HANDLERS.get(event.event_type)
            if handler:
                affected = handler(agents, event)
                logger.info(f"Step {step}: {event.event_type} '{event.name}' → {affected} agents affected")
                results.append((event, affected))
        return results
