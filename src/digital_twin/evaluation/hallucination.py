"""ハルシネーション検出 — 薬剤名・ガイドライン名の知識グラフ照合.

設計書 W7 Day1-2 に対応。LLM 回答中の固有名詞を
簡易知識グラフ（JSON マスタデータ）と照合し、
存在しない名称や誤った関連付けを検出する。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"


class FlagType(StrEnum):
    """ハルシネーションフラグの種類."""

    UNKNOWN_DRUG = "unknown_drug"
    UNKNOWN_GUIDELINE = "unknown_guideline"


@dataclass
class HallucinationFlag:
    """検出されたハルシネーション."""

    term: str
    flag_type: FlagType
    therapeutic_area: str
    context: str = ""  # 周辺テキスト


class HallucinationDetector:
    """LLM 回答中のハルシネーションを検出する."""

    def __init__(self, knowledge_dir: str | Path | None = None) -> None:
        knowledge_dir = Path(knowledge_dir) if knowledge_dir else _DEFAULT_KNOWLEDGE_DIR
        self._drugs = self._load_json(knowledge_dir / "drug_master.json")
        self._guidelines = self._load_json(knowledge_dir / "guideline_master.json")

    def _load_json(self, path: Path) -> dict[str, list[str]]:
        if not path.exists():
            logger.warning(f"知識ファイルが見つかりません: {path}")
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def get_known_drugs(self, therapeutic_area: str) -> set[str]:
        """指定疾患領域の既知薬剤名セット."""
        return set(self._drugs.get(therapeutic_area, []))

    def get_known_guidelines(self, therapeutic_area: str) -> set[str]:
        """指定疾患領域の既知ガイドライン名セット."""
        return set(self._guidelines.get(therapeutic_area, []))

    def check(
        self,
        response_text: str,
        therapeutic_area: str,
    ) -> list[HallucinationFlag]:
        """回答テキストからハルシネーションを検出する."""
        flags: list[HallucinationFlag] = []

        # 全疾患領域の薬剤名を収集（他領域の薬は OK）
        all_known_drugs: set[str] = set()
        for drugs in self._drugs.values():
            all_known_drugs.update(drugs)

        all_known_guidelines: set[str] = set()
        for guidelines in self._guidelines.values():
            all_known_guidelines.update(guidelines)

        # テキストからカタカナ語を抽出（薬剤名候補）
        katakana_pattern = re.compile(r"[ァ-ヴー]{3,}")
        katakana_terms = set(katakana_pattern.findall(response_text))

        for term in katakana_terms:
            # 一般的な医療用語は除外
            if term in _COMMON_MEDICAL_TERMS:
                continue
            # 既知薬剤に含まれない場合フラグ
            if term not in all_known_drugs and _looks_like_drug_name(term):
                flags.append(HallucinationFlag(
                    term=term,
                    flag_type=FlagType.UNKNOWN_DRUG,
                    therapeutic_area=therapeutic_area,
                ))

        # テキスト中の「ガイドライン」を含む固有名詞をチェック
        gl_pattern = re.compile(r"[^\s、。]{2,}ガイドライン")
        gl_mentions = set(gl_pattern.findall(response_text))
        for mention in gl_mentions:
            if not any(mention in known_gl or known_gl in mention for known_gl in all_known_guidelines):
                flags.append(HallucinationFlag(
                    term=mention,
                    flag_type=FlagType.UNKNOWN_GUIDELINE,
                    therapeutic_area=therapeutic_area,
                ))

        return flags


def _looks_like_drug_name(term: str) -> bool:
    """カタカナ語が薬剤名らしいかヒューリスティックに判定."""
    # 短すぎる / 長すぎるものは除外
    return not (len(term) < 4 or len(term) > 15)


# ハルシネーション検出から除外する一般的な医療用語
_COMMON_MEDICAL_TERMS = {
    "エビデンス", "ガイドライン", "プロトコル", "レジメン", "プロファイル",
    "バイオマーカー", "コンパニオン", "ゲノム", "モノクローナル", "ポリマー",
    "サイトカイン", "インターフェロン", "インターロイキン", "リンパ", "マクロファージ",
    "メタボリック", "シンドローム", "アレルギー", "アナフィラキシー",
    "ディテール", "チャネル", "シミュレーション", "プロモーション",
    "カテゴリー", "パターン", "スコア", "フィードバック", "コメント",
    "トレンド", "データ", "サンプル", "コントロール", "プラセボ",
    "ランダム", "ブラインド", "クロスオーバー", "フォローアップ",
    "エンドポイント", "サロゲート", "サブグループ", "ハザード",
    "クオリティ", "アドヒアランス", "コンプライアンス",
}
