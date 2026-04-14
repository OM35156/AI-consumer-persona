"""処方ポテンシャルモデル — 既存ロジスティック回帰モデルの読込・予測インターフェース.

設計書 Section 5.7 に対応。既存の処方ポテンシャルモデル（F1: 70-75%）を
joblib 形式で保存・読込し、施策プレテストの基盤として利用する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """モデルのメタデータ."""

    product: str
    target_disease: str
    feature_names: list[str]
    f1_score: float
    training_period: str


@dataclass
class PredictionResult:
    """予測結果."""

    score: float
    probability: float
    feature_contributions: dict[str, float] = field(default_factory=dict)


class PotentialModel:
    """処方ポテンシャルモデル（ロジスティック回帰）のラッパー."""

    def __init__(self, model_data: dict) -> None:
        self._model = model_data["model"]
        self.metadata = ModelMetadata(
            product=model_data["product"],
            target_disease=model_data["target_disease"],
            feature_names=model_data["feature_names"],
            f1_score=model_data["f1_score"],
            training_period=model_data["training_period"],
        )

    @classmethod
    def load(cls, path: str | Path) -> PotentialModel:
        """joblib ファイルからモデルを読み込む."""
        model_data = joblib.load(Path(path))
        return cls(model_data)

    def predict(self, features: dict[str, float]) -> PredictionResult:
        """特徴量辞書から処方ポテンシャルを予測する."""
        feature_vector = np.array([
            features.get(name, 0.0) for name in self.metadata.feature_names
        ]).reshape(1, -1)

        probability = float(self._model.predict_proba(feature_vector)[0, 1])
        contributions = self._calculate_contributions(features)

        return PredictionResult(
            score=probability,
            probability=probability,
            feature_contributions=contributions,
        )

    def get_coefficients(self) -> dict[str, float]:
        """モデル係数を取得する."""
        coefs = self._model.coef_[0]
        return dict(zip(self.metadata.feature_names, coefs, strict=True))

    def get_feature_importance(self) -> list[tuple[str, float]]:
        """特徴量重要度を降順で取得する."""
        coefs = self.get_coefficients()
        return sorted(coefs.items(), key=lambda x: abs(x[1]), reverse=True)

    def _calculate_contributions(self, features: dict[str, float]) -> dict[str, float]:
        """各特徴量の寄与度（係数 × 値）を計算する."""
        coefs = self.get_coefficients()
        return {
            name: coefs[name] * features.get(name, 0.0)
            for name in self.metadata.feature_names
        }


class PotentialModelRegistry:
    """複数の処方ポテンシャルモデルを管理するレジストリ."""

    def __init__(self) -> None:
        self._models: dict[str, PotentialModel] = {}

    def register(self, key: str, model: PotentialModel) -> None:
        """モデルを登録する."""
        self._models[key] = model

    def load_directory(self, directory: str | Path) -> int:
        """ディレクトリ内の全 joblib ファイルを読み込む."""
        directory = Path(directory)
        count = 0
        for path in directory.glob("*.joblib"):
            model = PotentialModel.load(path)
            key = f"{model.metadata.product}_{model.metadata.target_disease}"
            self.register(key, model)
            count += 1
            logger.info(f"Loaded model: {key} (F1={model.metadata.f1_score:.2f})")
        return count

    def get(self, product: str, disease: str) -> PotentialModel | None:
        """製品×疾患でモデルを取得する."""
        return self._models.get(f"{product}_{disease}")

    def list_models(self) -> list[str]:
        """登録済みモデルキーの一覧を返す."""
        return list(self._models.keys())
