from collections.abc import Sequence
from datetime import datetime

import numpy as np


def find_candidates(
    event_vector: np.ndarray,
    chain_vectors: np.ndarray,
    chain_ids: Sequence[int],
    last_updates: Sequence[datetime],
    t0: datetime,
    threshold: float,
    top_k: int = 3,
) -> list[int]:
    if chain_vectors.size == 0 or not chain_ids:
        return []
    scores = chain_vectors @ event_vector
    eligible: list[tuple[float, int]] = []
    for score, chain_id, last_update in zip(scores, chain_ids, last_updates, strict=True):
        if float(score) >= threshold and t0 > last_update:
            eligible.append((float(score), chain_id))
    eligible.sort(key=lambda item: item[0], reverse=True)
    return [chain_id for _, chain_id in eligible[:top_k]]
