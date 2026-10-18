import numpy as np


def nearest_event(
    embedding: np.ndarray,
    centroids: np.ndarray,
    threshold: float,
) -> int | None:
    if centroids.size == 0:
        return None
    normalized_centroids = _normalize_rows(centroids)
    normalized_embedding = _normalize(embedding)
    similarities = normalized_centroids @ normalized_embedding
    index = int(np.argmax(similarities))
    if float(similarities[index]) >= threshold:
        return index
    return None


def update_centroid(
    centroid: np.ndarray,
    n_sources: int,
    embedding: np.ndarray,
) -> np.ndarray:
    total = max(1, n_sources)
    updated = (centroid * total + embedding) / (total + 1)
    return _normalize(updated)


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return matrix / norms
