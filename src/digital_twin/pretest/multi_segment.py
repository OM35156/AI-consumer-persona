"""マルチセグメント比較 — 同一施策の複数セグメント並列評価.

設計書 W8 Day3-4 に対応。同一施策シナリオに対する複数セグメントの
反応を並列計算し、比較出力する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from digital_twin.pretest.potential_model import PotentialModel
from digital_twin.pretest.scenario_engine import PretestResult, PretestScenario, ScenarioEngine

logger = logging.getLogger(__name__)


@dataclass
class SegmentComparison:
    """セグメント比較結果."""

    segment_name: str
    result: PretestResult


@dataclass
class MultiSegmentResult:
    """マルチセグメント比較の全体結果."""

    scenario_name: str
    comparisons: list[SegmentComparison] = field(default_factory=list)

    def sorted_by_delta(self, descending: bool = True) -> list[SegmentComparison]:
        """delta の大きい順にソートした比較結果."""
        return sorted(self.comparisons, key=lambda c: c.result.delta, reverse=descending)

    def to_table(self) -> list[dict]:
        """比較テーブル形式で出力."""
        rows = []
        for comp in self.sorted_by_delta():
            top_features = sorted(
                comp.result.feature_contributions.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:3]
            rows.append({
                "セグメント": comp.segment_name,
                "ベーススコア": round(comp.result.base_score, 4),
                "シナリオ後": round(comp.result.new_score, 4),
                "変化量": round(comp.result.delta, 4),
                "主要寄与": ", ".join(f"{f}({v:+.3f})" for f, v in top_features),
            })
        return rows


class MultiSegmentComparator:
    """複数セグメントに対してシナリオを適用し比較する."""

    def __init__(self, model: PotentialModel) -> None:
        self._engine = ScenarioEngine(model)

    def compare(
        self,
        segments: list[dict],
        delta_features: dict[str, float],
        scenario_name: str = "",
    ) -> MultiSegmentResult:
        """複数セグメントに同一施策を適用し比較する.

        Args:
            segments: セグメントごとの base_features を含む辞書リスト
                      [{"name": "腫瘍内科・500床", "features": {...}}, ...]
            delta_features: 施策による特徴量変化
            scenario_name: シナリオ名
        """
        result = MultiSegmentResult(scenario_name=scenario_name)

        for seg in segments:
            scenario = PretestScenario(
                scenario_name=scenario_name,
                base_features=seg.get("features", {}),
                delta_features=delta_features,
            )
            pretest_result = self._engine.calculate_delta(scenario)
            result.comparisons.append(SegmentComparison(
                segment_name=seg.get("name", ""),
                result=pretest_result,
            ))

        return result
