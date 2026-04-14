"""Impact Track ローデータからデータカードを生成する ETL スクリプト."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from digital_twin.data.data_card import process_impact_track

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Impact Track → データカード JSONL")
    parser.add_argument("--input", type=Path, required=True, help="入力 CSV パス")
    parser.add_argument("--output", type=Path, default=Path("data/cards/impact_track.jsonl"), help="出力 JSONL パス")
    parser.add_argument("--min-sample", type=int, default=30, help="最低サンプル数")
    args = parser.parse_args()

    cards = process_impact_track(args.input, args.output, min_sample=args.min_sample)
    logging.info(f"生成完了: {len(cards)} カード")


if __name__ == "__main__":
    main()
