"""RAG コンテキストビルダー — 検索結果をプロンプト注入用テキストに組み立てる.

設計書 Section 7.1, 7.2 に対応。セグメントプロファイル（層①）と
ベクトルDB検索結果（層②）を統合し、確信度付きのコンテキストを生成する。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from digital_twin.data.segment_profile import SegmentProfile
from digital_twin.rag.search_client import PersonaSearchClient, SearchResult

logger = logging.getLogger(__name__)

# 確信度閾値（設計書 Section 7.2）
CONFIDENCE_HIGH = 0.60  # データ根拠あり
CONFIDENCE_MID = 0.40  # 推論


def confidence_label(score: float) -> str:
    """RAG 検索スコアから確信度ラベルを返す."""
    if score >= CONFIDENCE_HIGH:
        return "[データ根拠あり]"
    if score >= CONFIDENCE_MID:
        return "[推論]"
    return "[データ外]"


class ContextBuilder:
    """RAG コンテキストを組み立てるビルダー."""

    def __init__(
        self,
        search_client: PersonaSearchClient | None = None,
        profiles_dir: str | Path | None = None,
    ) -> None:
        self._search_client = search_client
        self._profiles_dir = Path(profiles_dir) if profiles_dir else None

    def load_segment_profile(self, segment: dict) -> SegmentProfile | None:
        """セグメント情報からプロファイル JSON を読み込む（層①）."""
        if not self._profiles_dir:
            return None

        specialty = segment.get("specialty", "")
        bed_size = segment.get("bed_size", "")
        age_range = segment.get("age_range", "")

        filename = f"{specialty}_{bed_size}_{age_range}.json"
        filepath = self._profiles_dir / filename

        if not filepath.exists():
            logger.warning(f"プロファイルが見つかりません: {filepath}")
            return None

        data = json.loads(filepath.read_text(encoding="utf-8"))
        return SegmentProfile.model_validate(data)

    def search_context(
        self,
        query_vector: list[float],
        segment: dict,
        product: str | None = None,
        top_k: int = 8,
    ) -> list[SearchResult]:
        """ベクトルDB からコンテキストを検索する（層②）."""
        if not self._search_client:
            return []

        return self._search_client.search(
            query_vector=query_vector,
            segment=segment,
            product=product,
            top_k=top_k,
        )

    def build_context_text(
        self,
        segment: dict,
        search_results: list[SearchResult] | None = None,
    ) -> str:
        """層① + 層② を統合したコンテキストテキストを生成する."""
        sections = []

        # 層①: セグメントプロファイル
        profile = self.load_segment_profile(segment)
        if profile:
            sections.append(profile.to_prompt_text())

        # 層②: RAG 検索結果
        if search_results:
            sections.append(self._format_search_results(search_results))

        # 回答ルール（確信度3段階）
        sections.append(self._response_rules())

        return "\n\n---\n\n".join(sections)

    def _format_search_results(self, results: list[SearchResult]) -> str:
        """検索結果をフォーマットする."""
        lines = [
            "## データコンテキスト（層②: ベクトルDB検索結果）",
            "以下は、あなたと同じセグメントの医師群の実際の調査データです。",
            "あなたの回答は、このデータの傾向と整合的でなければなりません。",
            "",
        ]

        for result in results:
            source = result.metadata.get("source", "unknown")
            score = result.score
            label = confidence_label(score)
            lines.append(f"[{source} | 関連度:{score:.2f}] {label}")
            lines.append(result.text)
            lines.append("")

        return "\n".join(lines)

    def _response_rules(self) -> str:
        """回答ルール（確信度3段階）."""
        return """## 回答ルール
1. 上記データに直接の根拠がある場合 → [データ根拠あり] と明示
2. データから合理的に推論できる場合 → [推論] と明示
3. データに根拠がない場合 → 「この点についてはデータ外の推測になります」と回答
4. 処方に関する数値は点推定ではなく幅で回答すること
5. 医学的に不正確な前提を含む質問には、前提の誤りを指摘すること"""
