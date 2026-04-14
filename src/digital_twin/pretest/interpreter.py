"""施策プレテスト解釈 — モデル出力 + RAG コンテキストの LLM 統合解釈.

設計書 W8 Day2-3 および Section 7.3「機能B: 施策プレテスト」に対応。
処方ポテンシャルモデルの出力と RAG 検索結果を LLM に渡し、
自然言語で施策効果の解釈・説明を生成する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from digital_twin.pretest.scenario_engine import PretestResult

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "pretest_interpretation.txt"


@dataclass
class InterpretationResult:
    """プレテスト解釈結果."""

    scenario_name: str
    interpretation_text: str
    base_score: float
    new_score: float
    delta: float
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class PretestInterpreter:
    """プレテスト結果を LLM で解釈するインタプリタ."""

    def __init__(
        self,
        llm_client: object | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2048,
        template_path: str | Path | None = None,
    ) -> None:
        self._client = llm_client
        self._model = model
        self._max_tokens = max_tokens
        self._template_path = Path(template_path) if template_path else _TEMPLATE_PATH
        self._template = self._load_template()

    def _load_template(self) -> str:
        if self._template_path.exists():
            return self._template_path.read_text(encoding="utf-8")
        logger.warning(f"テンプレートが見つかりません: {self._template_path}")
        return "施策プレテスト結果を解釈してください:\n{scenario_name}\nスコア変化: {delta:+.4f}"

    def build_prompt(
        self,
        result: PretestResult,
        rag_context: str = "",
    ) -> str:
        """解釈用のプロンプトを構築する."""
        # 特徴量寄与度のフォーマット
        contributions_lines = []
        sorted_contribs = sorted(
            result.feature_contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        for feat, contrib in sorted_contribs:
            direction = "+" if contrib > 0 else ""
            contributions_lines.append(f"  - {feat}: {direction}{contrib:.4f}")

        return self._template.format(
            scenario_name=result.scenario_name or "（名称なし）",
            base_score=result.base_score,
            new_score=result.new_score,
            delta=result.delta,
            feature_contributions="\n".join(contributions_lines) or "  （なし）",
            rag_context=rag_context or "（データなし）",
        )

    def interpret(
        self,
        result: PretestResult,
        rag_context: str = "",
    ) -> InterpretationResult:
        """プレテスト結果を LLM で解釈する."""
        prompt = self.build_prompt(result, rag_context)

        if self._client is None:
            # LLM クライアントがない場合はプロンプトのみ返す
            return InterpretationResult(
                scenario_name=result.scenario_name,
                interpretation_text=f"[LLM未接続] プロンプト生成済み（{len(prompt)}文字）",
                base_score=result.base_score,
                new_score=result.new_score,
                delta=result.delta,
            )

        import anthropic

        if isinstance(self._client, anthropic.Anthropic):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            return InterpretationResult(
                scenario_name=result.scenario_name,
                interpretation_text=text,
                base_score=result.base_score,
                new_score=result.new_score,
                delta=result.delta,
                model=self._model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

        return InterpretationResult(
            scenario_name=result.scenario_name,
            interpretation_text="[未対応のLLMクライアント]",
            base_score=result.base_score,
            new_score=result.new_score,
            delta=result.delta,
        )
