"""Doctor Mindscape ローデータからセグメントプロファイルを生成する ETL スクリプト."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from digital_twin.data.segment_profile import process_doctor_mindscape

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Doctor Mindscape → セグメントプロファイル JSON")
    parser.add_argument("--input", type=Path, required=True, help="入力 CSV パス")
    parser.add_argument("--output", type=Path, default=Path("data/profiles"), help="出力ディレクトリ")
    parser.add_argument("--min-sample", type=int, default=30, help="最低サンプル数")
    args = parser.parse_args()

    profiles = process_doctor_mindscape(args.input, args.output, min_sample=args.min_sample)
    logging.info(f"生成完了: {len(profiles)} セグメント → {args.output}")


if __name__ == "__main__":
    main()
