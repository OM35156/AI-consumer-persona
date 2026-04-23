"""データカード — ベクトルDB に格納するセグメント集計テキスト.

ローデータそのものは格納しない。セグメント単位で集計・加工し、
自然言語で記述した「データカード」を格納する。
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MIN_SAMPLE_SIZE = 30


class DataCard(BaseModel):
    """データカード（ベクトルDB に格納する単位）."""

    text: str
    metadata: dict


def generate_impact_track_card(
    product: str,
    channel: str,
    specialty: str,
    bed_size: str,
    month: str,
    n: int,
    intent_dist: dict[str, float],
    top_messages: dict[str, int],
    positive_messages: dict[str, int] | None = None,
) -> DataCard:
    """Impact Track データカードを生成する（設計書 Section 5.2 準拠）."""
    text = f"【{product}】{channel}チャネル ｜ {specialty}・{bed_size} ｜ {month}\n"
    text += f"サンプル数: {n}名\n\n"

    text += "■ 処方意向分布\n"
    for intent, ratio in intent_dist.items():
        text += f"  {intent}: {ratio:.0%}\n"

    text += "\n■ 主要メッセージ（上位5件）\n"
    for msg, count in list(top_messages.items())[:5]:
        text += f"  {msg}: {count}件（{count / n:.0%}）\n"

    if positive_messages:
        text += "\n■ 処方意向ポジティブ群の主要メッセージ\n"
        for msg, count in list(positive_messages.items())[:5]:
            text += f"  {msg}: {count}件\n"

    metadata = {
        "source": "impact_track",
        "product": product,
        "channel": channel,
        "specialty": specialty,
        "bed_size": bed_size,
        "month": month,
        "sample_n": n,
    }

    return DataCard(text=text, metadata=metadata)


def process_impact_track(
    input_path: str | Path,
    output_path: str | Path,
    aggregate_keys: list[str] | None = None,
    min_sample: int = MIN_SAMPLE_SIZE,
) -> list[DataCard]:
    """Impact Track CSV からデータカード JSONL を生成する."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if aggregate_keys is None:
        aggregate_keys = ["製品名", "チャネル", "主診療科", "病床数区分", "調査月"]

    df = pd.read_csv(input_path, encoding="utf-8")
    msg_cols = [c for c in df.columns if c.startswith("msg_")]

    cards: list[DataCard] = []

    for key, group_df in df.groupby(aggregate_keys):
        n = len(group_df)
        if n < min_sample:
            logger.info(f"スキップ: {key} (n={n} < {min_sample})")
            continue

        if isinstance(key, tuple):
            product, channel, specialty, bed_size, month = key
        else:
            product = str(key)
            channel = specialty = bed_size = month = ""

        # 処方意向分布
        intent_dist = group_df["処方意向"].value_counts(normalize=True).to_dict()

        # 主要メッセージ（上位5件）
        msg_counts = group_df[msg_cols].sum().sort_values(ascending=False).head(5)
        top_messages = {col.replace("msg_", ""): int(count) for col, count in msg_counts.items()}

        # ポジティブ群のメッセージ
        positive_messages = None
        pos_df = group_df[group_df["処方意向"].isin(["処方増やしたい", "新規に処方したい"])]
        if len(pos_df) > 10:
            pos_msg = pos_df[msg_cols].sum().sort_values(ascending=False).head(5)
            positive_messages = {col.replace("msg_", ""): int(count) for col, count in pos_msg.items()}

        card = generate_impact_track_card(
            product=str(product),
            channel=str(channel),
            specialty=str(specialty),
            bed_size=str(bed_size),
            month=str(month),
            n=n,
            intent_dist=intent_dist,
            top_messages=top_messages,
            positive_messages=positive_messages,
        )
        cards.append(card)

    # JSONL 出力
    with output_path.open("w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card.model_dump(), ensure_ascii=False) + "\n")

    logger.info(f"生成完了: {len(cards)} カード → {output_path}")
    return cards


# --- SOC データカード（設計書 Section 5.3） ---


def generate_soc_card(
    product: str,
    specialty: str,
    bed_size: str,
    quarter: str,
    n: int,
    impression_dist: dict[str, float],
    channel_influence: dict[str, float],
    non_promo_influence: dict[str, float] | None = None,
) -> DataCard:
    """SOC（ブランド想起）データカードを生成する."""
    text = f"【{product}】ブランド想起 ｜ {specialty}・{bed_size} ｜ {quarter}\n"
    text += f"想起医師数（推計）: {n}名\n\n"

    text += "■ 製品印象（想起した医師の評価）\n"
    for level, ratio in impression_dist.items():
        text += f"  {level}: {ratio:.0%}\n"

    text += "\n■ 想起に影響したチャネル（影響度スコア: 5段階平均）\n"
    for ch, score in sorted(channel_influence.items(), key=lambda x: -x[1]):
        text += f"  {ch}: {score:.1f}/5.0\n"

    if non_promo_influence:
        text += "\n■ ノンプロモーション影響\n"
        for ch, score in sorted(non_promo_influence.items(), key=lambda x: -x[1]):
            text += f"  {ch}: {score:.1f}/5.0\n"

    metadata = {
        "source": "soc",
        "product": product,
        "specialty": specialty,
        "bed_size": bed_size,
        "month": quarter,
        "sample_n": n,
    }

    return DataCard(text=text, metadata=metadata)


# --- Rep-i データカード（設計書 Section 5.4） ---


def generate_repi_card(
    maker: str,
    specialty: str,
    bed_size: str,
    period: str,
    n: int,
    overall_eval: dict[str, float],
    item_scores: dict[str, float],
    improvement_areas: dict[str, float] | None = None,
) -> DataCard:
    """Rep-i（MR評価）データカードを生成する."""
    text = f"【{maker}】MR評価 ｜ {specialty}・{bed_size} ｜ {period}\n"
    text += f"評価医師数: {n}名\n\n"

    text += "■ MR総合評価\n"
    for level, ratio in overall_eval.items():
        text += f"  {level}: {ratio:.0%}\n"

    text += "\n■ 項目別評価（高評価率上位）\n"
    for item, score in sorted(item_scores.items(), key=lambda x: -x[1])[:8]:
        text += f"  {item}: {score:.0%}\n"

    if improvement_areas:
        text += "\n■ 普通評価MRの要改善要素（上位）\n"
        for area, ratio in sorted(improvement_areas.items(), key=lambda x: -x[1])[:5]:
            text += f"  {area}: {ratio:.0%}\n"

    metadata = {
        "source": "repi",
        "product": maker,
        "specialty": specialty,
        "bed_size": bed_size,
        "month": period,
        "sample_n": n,
    }

    return DataCard(text=text, metadata=metadata)


# --- Logscape データカード（設計書 Section 5.5） ---


def generate_logscape_card(
    specialty: str,
    bed_size: str,
    month: str,
    n: int,
    site_ranking: list[tuple[str, float]],
    search_keywords: list[tuple[str, int]],
    journey_patterns: list[tuple[str, float]] | None = None,
) -> DataCard:
    """Logscape（デジタル行動）データカードを生成する."""
    text = f"【デジタル行動】{specialty}・{bed_size} ｜ {month}\n"
    text += f"対象医師数: {n}名\n\n"

    text += "■ 医療関連サイト滞在時間ランキング（月間平均/人）\n"
    for site, minutes in site_ranking[:10]:
        text += f"  {site}: {minutes:.0f}分\n"

    text += "\n■ 頻出検索ワード（医療関連）\n"
    for word, count in search_keywords[:10]:
        text += f"  {word}: {count}名が検索\n"

    if journey_patterns:
        text += "\n■ サイト遷移パターン（上位）\n"
        for pattern, ratio in journey_patterns[:5]:
            text += f"  {pattern}: {ratio:.0%}\n"

    metadata = {
        "source": "logscape",
        "specialty": specialty,
        "bed_size": bed_size,
        "month": month,
        "sample_n": n,
    }

    return DataCard(text=text, metadata=metadata)


# --- クロス集計データカード（設計書 Section 5.6） ---


def generate_cross_card(
    product: str,
    specialty: str,
    bed_size: str,
    period: str,
    n: int,
    cross_stats: dict[str, float],
) -> DataCard:
    """クロス集計データカードを生成する（シングルソース紐づけ）."""
    text = f"【クロス分析】{product} ｜ {specialty}・{bed_size} ｜ {period}\n"
    text += f"対象医師数: {n}名\n\n"

    if "high_mr_pos_intent" in cross_stats:
        text += "■ MR評価×処方意向\n"
        text += f"  MR高評価群の処方意向ポジティブ率: {cross_stats['high_mr_pos_intent']:.0%}\n"
        text += f"  MR低評価群の処方意向ポジティブ率: {cross_stats.get('low_mr_pos_intent', 0):.0%}\n\n"

    if "early_web_recall" in cross_stats:
        text += "■ 新薬受容性×チャネル反応\n"
        text += f"  受容性「早期処方」群のWeb講演会想起率: {cross_stats['early_web_recall']:.0%}\n"
        text += f"  受容性「様子見」群のWeb講演会想起率: {cross_stats.get('late_web_recall', 0):.0%}\n\n"

    if "recall_to_rx" in cross_stats:
        text += "■ 想起→新規処方の転換率\n"
        text += f"  想起あり群の新規処方率: {cross_stats['recall_to_rx']:.0%}\n"
        text += f"  想起なし群の新規処方率: {cross_stats.get('no_recall_to_rx', 0):.0%}\n"

    metadata = {
        "source": "cross_analysis",
        "product": product,
        "specialty": specialty,
        "bed_size": bed_size,
        "month": period,
        "sample_n": n,
    }

    return DataCard(text=text, metadata=metadata)


# --- toitta インタビューデータカード ---


def generate_toitta_card(
    topic: str,
    slices: list[str],
    n_interviewees: int,
    domain: str = "sleep",
) -> DataCard:
    """toitta インタビュー切片からトピック単位のデータカードを生成する."""
    text = f"【睡眠インタビュー】トピック: {topic}\n"
    text += f"対象者数: {n_interviewees}名 / 発言数: {len(slices)}件\n\n"
    text += "■ 生活者の声\n"
    for s in slices:
        text += f"  - {s}\n"

    metadata = {
        "source": "toitta",
        "topic": topic,
        "domain": domain,
        "n_interviewees": n_interviewees,
        "sample_n": len(slices),
    }

    return DataCard(text=text, metadata=metadata)


def process_toitta_interviews(
    input_dir: str | Path,
    output_path: str | Path,
    glob_pattern: str = "*睡眠対策インタビュー*.csv",
) -> list[DataCard]:
    """toitta エクスポート CSV 群からデータカード JSONL を生成する."""
    input_dir = Path(input_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob(glob_pattern))
    if not csv_files:
        logger.warning(f"CSV が見つかりません: {input_dir / glob_pattern}")
        return []

    # トピック別に集約: {topic: {interviewee_id: [slice_text, ...]}}
    topic_map: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for csv_path in csv_files:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        for _, row in df.iterrows():
            slice_text = str(row["切片"]).strip()
            if not slice_text:
                continue

            interviewee_id = str(row.get("インタビュータイトル", csv_path.stem))

            raw_groups = str(row.get("グループ名(JSON)", "[]"))
            try:
                groups = json.loads(raw_groups)
            except (json.JSONDecodeError, TypeError):
                groups = []

            if not groups:
                topic_map["未分類"][interviewee_id].append(slice_text)
            else:
                for group_name in groups:
                    topic_map[group_name][interviewee_id].append(slice_text)

    cards: list[DataCard] = []
    for topic, interviewees in sorted(topic_map.items()):
        all_slices = [s for ss in interviewees.values() for s in ss]
        card = generate_toitta_card(
            topic=topic,
            slices=all_slices,
            n_interviewees=len(interviewees),
        )
        cards.append(card)

    with output_path.open("w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card.model_dump(), ensure_ascii=False) + "\n")

    logger.info(f"生成完了: {len(cards)} カード → {output_path}")
    return cards
