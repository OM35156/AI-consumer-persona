"""確信度スコアリングシステム — RAG relevance score ベース.

設計書 Section 7.2 に対応。検索スコアに基づき回答の確信度を3段階で自動判定する。
閾値は configs/base.yaml から設定可能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from digital_twin.rag.search_client import SearchResult

# デフォルト閾値
DEFAULT_HIGH_THRESHOLD = 0.60
DEFAULT_MID_THRESHOLD = 0.40


class ConfidenceLevel(StrEnum):
    """確信度レベル."""

    DATA_GROUNDED = "data_grounded"  # データ根拠あり
    INFERRED = "inferred"  # 推論
    OUT_OF_DATA = "out_of_data"  # データ外


@dataclass
class ConfidenceResult:
    """確信度判定結果."""

    level: ConfidenceLevel
    label: str  # 日本語ラベル
    score: float  # 元のスコア
    evidence_sources: list[str] = field(default_factory=list)


# 日本語ラベルマッピング
_LABELS = {
    ConfidenceLevel.DATA_GROUNDED: "[データ根拠あり]",
    ConfidenceLevel.INFERRED: "[推論]",
    ConfidenceLevel.OUT_OF_DATA: "[データ外]",
}


class ConfidenceScorer:
    """RAG 検索結果から確信度を判定するスコアラー."""

    def __init__(
        self,
        high_threshold: float = DEFAULT_HIGH_THRESHOLD,
        mid_threshold: float = DEFAULT_MID_THRESHOLD,
    ) -> None:
        self.high_threshold = high_threshold
        self.mid_threshold = mid_threshold

    def score_single(self, relevance_score: float) -> ConfidenceLevel:
        """単一スコアから確信度レベルを判定する."""
        if relevance_score >= self.high_threshold:
            return ConfidenceLevel.DATA_GROUNDED
        if relevance_score >= self.mid_threshold:
            return ConfidenceLevel.INFERRED
        return ConfidenceLevel.OUT_OF_DATA

    def score_results(self, results: list[SearchResult]) -> ConfidenceResult:
        """複数の検索結果から総合的な確信度を判定する."""
        if not results:
            return ConfidenceResult(
                level=ConfidenceLevel.OUT_OF_DATA,
                label=_LABELS[ConfidenceLevel.OUT_OF_DATA],
                score=0.0,
            )

        avg_score = sum(r.score for r in results) / len(results)
        max_score = max(r.score for r in results)

        # 最高スコアで判定（1件でも高品質なデータがあれば信頼度を上げる）
        level = self.score_single(max_score)

        sources = list({r.metadata.get("source", "") for r in results if r.metadata.get("source")})

        return ConfidenceResult(
            level=level,
            label=_LABELS[level],
            score=avg_score,
            evidence_sources=sources,
        )

    def get_label(self, level: ConfidenceLevel) -> str:
        """確信度レベルの日本語ラベルを返す."""
        return _LABELS.get(level, "[不明]")
