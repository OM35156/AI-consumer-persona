"""施策シナリオ → ポテンシャル変化算出エンジン.

設計書 W8 Day1-2 に対応。施策シナリオ入力に対し、
処方ポテンシャルモデルの係数でスコア変化（delta）を算出する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from digital_twin.pretest.potential_model import PotentialModel, PredictionResult


class PretestScenario(BaseModel):
    """施策プレテストのシナリオ定義."""

    scenario_name: str = ""
    base_features: dict[str, float] = {}
    delta_features: dict[str, float] = {}  # 変化させる特徴量と変化量


@dataclass
class PretestResult:
    """プレテスト結果."""

    scenario_name: str
    base_score: float
    new_score: float
    delta: float
    base_prediction: PredictionResult
    new_prediction: PredictionResult
    feature_contributions: dict[str, float] = field(default_factory=dict)


class ScenarioEngine:
    """施策シナリオからポテンシャル変化を算出するエンジン."""

    def __init__(self, model: PotentialModel) -> None:
        self._model = model

    def calculate_delta(self, scenario: PretestScenario) -> PretestResult:
        """シナリオに基づきスコア変化を算出する."""
        # ベーススコア
        base_prediction = self._model.predict(scenario.base_features)

        # シナリオ適用後の特徴量
        new_features = dict(scenario.base_features)
        for feat, delta_val in scenario.delta_features.items():
            new_features[feat] = new_features.get(feat, 0.0) + delta_val

        new_prediction = self._model.predict(new_features)

        # 特徴量ごとの寄与度変化
        contributions = {}
        coefs = self._model.get_coefficients()
        for feat, delta_val in scenario.delta_features.items():
            contributions[feat] = coefs.get(feat, 0.0) * delta_val

        return PretestResult(
            scenario_name=scenario.scenario_name,
            base_score=base_prediction.score,
            new_score=new_prediction.score,
            delta=new_prediction.score - base_prediction.score,
            base_prediction=base_prediction,
            new_prediction=new_prediction,
            feature_contributions=contributions,
        )

    def calculate_batch(
        self,
        scenarios: list[PretestScenario],
    ) -> list[PretestResult]:
        """複数シナリオのバッチ計算."""
        return [self.calculate_delta(s) for s in scenarios]
