from dataclasses import dataclass

import numpy as np

from back.ml.classifier import CategoryClassifier
from back.ml.embeddings import E5Embedder
from back.ml.lemmatizer import LemmaIndex


@dataclass(frozen=True, slots=True)
class NewsEnrichment:
    categories: dict[str, float]
    lemmas: list[str]
    embedding: np.ndarray


class NewsEnricher:
    def __init__(
        self,
        classifier: CategoryClassifier,
        embedder: E5Embedder,
        lemmatizer: LemmaIndex,
    ) -> None:
        self._classifier = classifier
        self._embedder = embedder
        self._lemmatizer = lemmatizer

    def enrich(self, title: str, text: str) -> NewsEnrichment:
        payload = f"{title}\n{text}".strip()
        categories = self._classifier.predict([payload])[0]
        embedding = self._embedder.embed_passages([payload])[0]
        return NewsEnrichment(
            categories=categories,
            lemmas=self._lemmatizer.lemmas(payload),
            embedding=embedding,
        )
