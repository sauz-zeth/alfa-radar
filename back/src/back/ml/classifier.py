from collections.abc import Mapping, Sequence

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class CategoryClassifier:
    def __init__(
        self,
        model_name: str,
        thresholds: Mapping[str, float],
        device: str | None = None,
    ) -> None:
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
        self._model.eval()
        self._thresholds = dict(thresholds)
        labels = self._model.config.id2label
        self._labels = [labels[index] for index in range(len(labels))]

    @property
    def thresholds(self) -> dict[str, float]:
        return dict(self._thresholds)

    def predict(self, texts: Sequence[str], batch_size: int = 16) -> list[dict[str, float]]:
        results: list[dict[str, float]] = []
        with torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                batch = list(texts[start : start + batch_size])
                encoded = self._tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )
                encoded = {key: value.to(self._device) for key, value in encoded.items()}
                logits = self._model(**encoded).logits
                probabilities = torch.sigmoid(logits).cpu().numpy()
                for row in probabilities:
                    results.append(
                        {
                            label: float(score)
                            for label, score in zip(self._labels, row, strict=True)
                        }
                    )
        return results

    def adjusted(self, scores: Mapping[str, float]) -> dict[str, float]:
        adjusted: dict[str, float] = {}
        for category, probability in scores.items():
            threshold = self._thresholds.get(category, 0.0)
            if threshold >= 1.0 or probability <= threshold:
                adjusted[category] = 0.0
                continue
            adjusted[category] = (probability - threshold) / (1.0 - threshold)
        return adjusted

    def neg_logits_to_probabilities(self, logits: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-logits))
