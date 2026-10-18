from collections.abc import Sequence

import numpy as np


class E5Embedder:
    def __init__(self, model_name: str, device: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, device=device)

    def embed_passages(self, texts: Sequence[str]) -> np.ndarray:
        prepared = [f"passage: {text}" for text in texts]
        vectors = self._model.encode(
            prepared,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)

    def embed_queries(self, texts: Sequence[str]) -> np.ndarray:
        prepared = [f"query: {text}" for text in texts]
        vectors = self._model.encode(
            prepared,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32)
