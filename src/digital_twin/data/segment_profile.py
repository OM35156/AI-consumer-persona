"""セグメントプロファイル — Doctor Mindscape データから生成する層①データ.

ベクトルDB には格納せず、システムプロンプトに直接埋め込む。
セグメント = 主診療科 × 病床数区分 × 年代。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MIN_SAMPLE_SIZE = 30


class PatientDistribution(BaseModel):
    """疾患×薬効の月間患者数分布."""

    disease_drug: str
    median: float
    p25: float
    p75: float


class NewDrugReceptivity(BaseModel):
    """新薬受容性の分布（5段階）."""

    early_prescriber: float = 0.0
    relatively_early: float = 0.0
    wait_and_see: float = 0.0
    majority_prescribes: float = 0.0
    after_established: float = 0.0


class SegmentProfile(BaseModel):
    """セグメントプロファイル（層①）."""

    specialty: str
    bed_size: str
    age_range: str
    estimated_population: int = 0
    patient_distributions: list[PatientDistribution] = []
    new_drug_receptivity: NewDrugReceptivity = Field(default_factory=NewDrugReceptivity)
    mr_contact: dict[str, float] = {}

    def to_prompt_text(self) -> str:
        """プロンプト注入用のテキストを生成する."""
        lines = [
            f"## セグメントプロファイル（{self.specialty}・{self.bed_size}・{self.age_range}）",
            f"推計人口: {self.estimated_population}名",
        ]

        if self.patient_distributions:
            lines.append("\n### 月間患者数分布")
            for pd_ in self.patient_distributions:
                lines.append(f"  {pd_.disease_drug}: 中央値 {pd_.median:.0f}名 (25%tile: {pd_.p25:.0f}, 75%tile: {pd_.p75:.0f})")

        ndr = self.new_drug_receptivity
        lines.append("\n### 新薬受容性")
        lines.append(f"  いち早く処方: {ndr.early_prescriber:.0%}")
        lines.append(f"  比較的早く処方: {ndr.relatively_early:.0%}")
        lines.append(f"  様子を見てから: {ndr.wait_and_see:.0%}")
        lines.append(f"  大多数が処方してから: {ndr.majority_prescribes:.0%}")
        lines.append(f"  実績確立後: {ndr.after_established:.0%}")

        if self.mr_contact:
            lines.append("\n### MR面談カバー率（上位）")
            for company, rate in sorted(self.mr_contact.items(), key=lambda x: -x[1])[:10]:
                lines.append(f"  {company}: {rate:.0%}")

        return "\n".join(lines)


def build_profile_from_group(
    group_df: pd.DataFrame,
    specialty: str,
    bed_size: str,
    age_range: str,
    patient_columns: list[str] | None = None,
    mr_columns: list[str] | None = None,
) -> SegmentProfile:
    """DataFrame のグループからセグメントプロファイルを構築する."""
    # 推計医師数
    estimated = int(group_df["拡大推計係数"].sum()) if "拡大推計係数" in group_df.columns else len(group_df)

    # 患者数分布
    distributions = []
    if patient_columns is None:
        patient_columns = [c for c in group_df.columns if c.startswith("患者数_")]
    for col in patient_columns:
        vals = group_df[col].dropna()
        if len(vals) == 0:
            continue
        disease_drug = col.replace("患者数_", "")
        distributions.append(PatientDistribution(
            disease_drug=disease_drug,
            median=float(vals.median()),
            p25=float(vals.quantile(0.25)),
            p75=float(vals.quantile(0.75)),
        ))

    # 新薬受容性
    ndr = NewDrugReceptivity()
    if "新薬受容性" in group_df.columns:
        counts = group_df["新薬受容性"].value_counts(normalize=True)
        ndr = NewDrugReceptivity(
            early_prescriber=float(counts.get("いち早く処方", 0)),
            relatively_early=float(counts.get("比較的早く処方", 0)),
            wait_and_see=float(counts.get("様子を見てから", 0)),
            majority_prescribes=float(counts.get("大多数が処方してから", 0)),
            after_established=float(counts.get("実績確立後", 0)),
        )

    # MR面談カバー率
    mr = {}
    if mr_columns is None:
        mr_columns = [c for c in group_df.columns if c.startswith("MR面談_")]
    for col in mr_columns:
        company = col.replace("MR面談_", "")
        mr[company] = float(group_df[col].mean())

    return SegmentProfile(
        specialty=specialty,
        bed_size=bed_size,
        age_range=age_range,
        estimated_population=estimated,
        patient_distributions=distributions,
        new_drug_receptivity=ndr,
        mr_contact=mr,
    )


def process_doctor_mindscape(
    input_path: str | Path,
    output_dir: str | Path,
    segment_keys: list[str] | None = None,
    min_sample: int = MIN_SAMPLE_SIZE,
) -> list[SegmentProfile]:
    """Doctor Mindscape CSV からセグメントプロファイル JSON を生成する."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if segment_keys is None:
        segment_keys = ["主診療科", "病床数区分", "年代"]

    df = pd.read_csv(input_path, encoding="utf-8")
    profiles: list[SegmentProfile] = []

    for seg_key, seg_df in df.groupby(segment_keys):
        if len(seg_df) < min_sample:
            logger.info(f"スキップ: {seg_key} (n={len(seg_df)} < {min_sample})")
            continue

        if isinstance(seg_key, tuple):
            specialty, bed_size, age_range = seg_key[0], seg_key[1], seg_key[2]
        else:
            specialty, bed_size, age_range = str(seg_key), "", ""

        profile = build_profile_from_group(seg_df, specialty, bed_size, age_range)
        profiles.append(profile)

        filename = f"{specialty}_{bed_size}_{age_range}.json"
        filepath = output_dir / filename
        filepath.write_text(
            json.dumps(profile.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"生成: {filepath}")

    return profiles
