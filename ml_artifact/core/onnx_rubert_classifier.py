"""ONNX Runtime inference for the fine-tuned ruBERT multilabel classifier."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class RubertOnnxClassifier:
    def __init__(
        self,
        model_dir: Path | str,
        providers: list[str] | None = None,
        model_filename: str = "model.onnx",
    ) -> None:
        self.model_dir = Path(model_dir)
        metadata_path = self.model_dir / "metadata.json"
        self.metadata: dict[str, Any] = json.loads(metadata_path.read_text(encoding="utf-8"))
        label_map = self.metadata["label_map"]
        self.labels = [label_map[str(index)] for index in range(len(label_map))]
        self.thresholds = np.asarray(
            [self.metadata["thresholds"][label] for label in self.labels], dtype=np.float32
        )
        self.max_length = int(self.metadata["config"]["max_length"])
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir / "tokenizer")
        self.session = ort.InferenceSession(
            str(self.model_dir / model_filename),
            providers=providers or ["CPUExecutionProvider"],
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        required = {"input_ids", "attention_mask"}
        if not required.issubset(self.input_names):
            raise ValueError(f"ONNX model must accept {sorted(required)}")

    def predict_logits(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, len(self.labels)), dtype=np.float32)
        if any(not isinstance(text, str) for text in texts):
            raise TypeError("Every input must be a string")

        encoded = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="np",
        )
        feed = {
            name: encoded[name].astype(np.int64, copy=False)
            for name in self.input_names
            if name in encoded
        }
        if "token_type_ids" in self.input_names and "token_type_ids" not in feed:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"])
        return self.session.run(["logits"], feed)[0]

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        logits = self.predict_logits(texts)
        return (1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))).astype(np.float32)

    def predict(self, texts: list[str]) -> list[dict[str, Any]]:
        probabilities = self.predict_proba(texts)
        results = []
        for row in probabilities:
            selected = [
                {"label": label, "score": float(score)}
                for label, score, threshold in zip(self.labels, row, self.thresholds, strict=True)
                if score >= threshold
            ]
            results.append(
                {
                    "labels": selected,
                    "probabilities": {
                        label: float(score)
                        for label, score in zip(self.labels, row, strict=True)
                    },
                }
            )
        return results
