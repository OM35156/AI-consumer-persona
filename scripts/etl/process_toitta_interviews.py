"""toitta インタビュー CSV からデータカードを生成する ETL スクリプト."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from digital_twin.data.data_card import process_toitta_interviews

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="toitta インタビュー CSV → データカード JSONL")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/"), help="入力 CSV ディレクトリ")
    parser.add_argument("--output", type=Path, default=Path("data/cards/toitta_sleep_interviews.jsonl"), help="出力 JSONL パス")
    parser.add_argument("--glob-pattern", default="*睡眠対策インタビュー*.csv", help="CSV ファイル名パターン")
    args = parser.parse_args()

    cards = process_toitta_interviews(args.input_dir, args.output, args.glob_pattern)
    logging.info(f"生成完了: {len(cards)} カード")


if __name__ == "__main__":
    main()
