"""全データカードをエンベッドし Qdrant に投入するスクリプト.

設計書 Section 6 に対応。data/cards/ 内の全 JSONL を読込、
multilingual-e5-large でエンベッドし、Qdrant に upsert する。
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_cards(cards_dir: Path) -> list[dict]:
    """data/cards/ 内の全 JSONL ファイルからカードを読み込む."""
    cards = []
    for jsonl_path in sorted(cards_dir.glob("*.jsonl")):
        with jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    cards.append(json.loads(line))
        logger.info(f"読込: {jsonl_path.name} ({len(cards)} cards total)")
    return cards


def main() -> None:
    parser = argparse.ArgumentParser(description="データカード → Qdrant 投入")
    parser.add_argument("--cards-dir", type=Path, default=Path("data/cards"), help="カードディレクトリ")
    parser.add_argument("--host", default="localhost", help="Qdrant ホスト")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant ポート")
    parser.add_argument("--collection", default="persona_knowledge", help="コレクション名")
    parser.add_argument("--embedding-model", default="intfloat/multilingual-e5-large", help="Embedding モデル")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding バッチサイズ")
    args = parser.parse_args()

    # カード読込
    cards = load_cards(args.cards_dir)
    if not cards:
        logger.warning("カードが見つかりません")
        return

    logger.info(f"合計 {len(cards)} カードを投入します")

    # Embedding
    from digital_twin.rag.embedder import Embedder

    embedder = Embedder(model_name=args.embedding_model)

    texts = [c["text"] for c in cards]
    logger.info(f"Embedding 開始 (dim={embedder.dimension})...")
    vectors = embedder.encode_batch(texts, batch_size=args.batch_size)
    logger.info("Embedding 完了")

    # Qdrant 投入
    from digital_twin.rag.search_client import PersonaSearchClient

    client = PersonaSearchClient(backend="qdrant_local", host=args.host, port=args.port)
    client.ensure_collection(collection_name=args.collection, vector_size=embedder.dimension)

    points = [
        {
            "id": i,
            "vector": vectors[i],
            "payload": {"text": cards[i]["text"], **cards[i]["metadata"]},
        }
        for i in range(len(cards))
    ]

    count = client.upsert(points, collection_name=args.collection)
    logger.info(f"投入完了: {count} ポイント → {args.collection}")


if __name__ == "__main__":
    main()
