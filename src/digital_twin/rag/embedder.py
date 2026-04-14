"""Embedding ラッパー — sentence-transformers による日本語テキストのベクトル化.

設計書 Section 6 に対応。intfloat/multilingual-e5-large (dim=1024) を使用。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class Embedder:
    """テキストを密ベクトルに変換するラッパークラス."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        logger.info(f"Embedding モデルを読込: {model_name}")

    @property
    def dimension(self) -> int:
        """ベクトル次元数."""
        return self._model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> list[float]:
        """単一テキストをエンベッドする（query: プレフィックス付き）."""
        embedding = self._model.encode(
            f"query: {text}",
            normalize_embeddings=True,
        )
        return embedding.tolist()

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """複数テキストをバッチでエンベッドする."""
        prefixed = [f"query: {t}" for t in texts]
        embeddings = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
        )
        return [e.tolist() for e in embeddings]
