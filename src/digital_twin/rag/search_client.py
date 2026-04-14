"""ベクトルDB 検索クライアントの抽象化レイヤー.

Qdrant（ローカル）と将来の GCP Vertex AI Matching Engine への
差し替えを容易にするための共通インターフェースを提供する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)

# メタデータインデックス定義
_KEYWORD_FIELDS = ["source", "product", "specialty", "bed_size", "month"]
_INTEGER_FIELDS = ["sample_n"]


@dataclass
class SearchResult:
    """ベクトル検索結果の1件."""

    text: str
    score: float
    metadata: dict = field(default_factory=dict)


class PersonaSearchClient:
    """ペルソナ知識ベースのベクトル検索クライアント.

    backend パラメータで Qdrant / Vertex AI を切り替え可能。
    """

    def __init__(
        self,
        backend: str = "qdrant_local",
        host: str = "localhost",
        port: int = 6333,
    ) -> None:
        if backend == "qdrant_local":
            self._client = QdrantClient(host=host, port=port)
            self._backend = backend
        elif backend == "qdrant_memory":
            self._client = QdrantClient(":memory:")
            self._backend = backend
        else:
            raise ValueError(f"未対応のバックエンド: {backend}")

    def ensure_collection(
        self,
        collection_name: str = "persona_knowledge",
        vector_size: int = 1024,
    ) -> None:
        """コレクションが存在しなければ作成し、メタデータインデックスを設定する."""
        collections = self._client.get_collections().collections
        existing = {c.name for c in collections}

        if collection_name not in existing:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"コレクション '{collection_name}' を作成しました（dim={vector_size}）")

        # メタデータインデックス作成
        for field_name in _KEYWORD_FIELDS:
            self._client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD,
            )
        for field_name in _INTEGER_FIELDS:
            self._client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=PayloadSchemaType.INTEGER,
            )

    def search(
        self,
        query_vector: list[float],
        segment: dict,
        product: str | None = None,
        top_k: int = 8,
        score_threshold: float = 0.35,
        collection_name: str = "persona_knowledge",
    ) -> list[SearchResult]:
        """セグメント情報でフィルタリングしながらベクトル検索を実行する."""
        must_conditions: list[FieldCondition] = []

        if segment.get("specialty"):
            must_conditions.append(
                FieldCondition(key="specialty", match=MatchValue(value=segment["specialty"]))
            )
        if segment.get("bed_size"):
            must_conditions.append(
                FieldCondition(key="bed_size", match=MatchValue(value=segment["bed_size"]))
            )
        if product:
            must_conditions.append(
                FieldCondition(key="product", match=MatchValue(value=product))
            )

        query_filter = Filter(must=must_conditions) if must_conditions else None

        response = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        return [
            SearchResult(
                text=hit.payload.get("text", ""),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() if k != "text"},
            )
            for hit in response.points
        ]

    def upsert(
        self,
        points: list[dict],
        collection_name: str = "persona_knowledge",
        batch_size: int = 1000,
    ) -> int:
        """ポイントをバッチで upsert する.

        Args:
            points: 各要素は {"id": int, "vector": list[float], "payload": dict}
            collection_name: 対象コレクション名
            batch_size: バッチサイズ

        Returns:
            投入したポイント数
        """
        total = 0
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            structs = [
                PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p["payload"],
                )
                for p in batch
            ]
            self._client.upsert(collection_name=collection_name, points=structs)
            total += len(structs)
            logger.info(f"Upserted {total}/{len(points)} points")

        return total
