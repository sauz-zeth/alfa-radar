"""BGE-M3 embeddings and online cosine/reranker clustering."""

from __future__ import annotations

from typing import Any
from pathlib import Path

try:
    from .news_data import EventCluster
except ImportError:
    from news_data import EventCluster
from datetime import timedelta

import numpy as np
try:
    from .image_utils import CLUSTER_IMAGE_EXCLUDED_SOURCES, image_source_is_excluded, same_image
except ImportError:
    from image_utils import CLUSTER_IMAGE_EXCLUDED_SOURCES, image_source_is_excluded, same_image

MODEL_ROOT = Path(__file__).resolve().parent.parent / "models"
EMBEDDING_MODEL = str(MODEL_ROOT / "bge_m3_int8")
RERANKER_MODEL = str(MODEL_ROOT / "bge_reranker_int8")
DEFAULT_COSINE_THRESHOLD = 0.78
DEFAULT_RERANKER_THRESHOLD = 0.0  # Raw logit, not a probability.


def _resolve_model(model_name: str) -> str:
    path = Path(model_name).expanduser().resolve()
    if not (path / "model_quantized.onnx").is_file():
        raise FileNotFoundError(f"Local ONNX model not found: {path}")
    return str(path)


class OnnxEmbedder:
    def __init__(self, model_name: str = EMBEDDING_MODEL, max_length: int = 512) -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        model_dir = _resolve_model(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.session = ort.InferenceSession(
            f"{model_dir}/model_quantized.onnx", providers=["CPUExecutionProvider"]
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        self.max_length = max_length

    def encode(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        outputs = []
        for offset in range(0, len(texts), batch_size):
            encoded = self.tokenizer(
                texts[offset:offset + batch_size], padding=True, truncation=True,
                max_length=self.max_length, return_tensors="np",
            )
            feeds = {key: value.astype(np.int64) for key, value in encoded.items()
                     if key in self.input_names}
            token_embeddings = self.session.run(None, feeds)[0]
            # Match deepvk/USER-bge-m3 Sentence Transformers config: CLS pooling.
            pooled = token_embeddings[:, 0, :]
            norms = np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)
            outputs.append((pooled / norms).astype(np.float32))
        return np.concatenate(outputs) if outputs else np.empty((0, 1024), dtype=np.float32)


class LocalReranker:
    def __init__(self, model_name: str = RERANKER_MODEL, device: str = "cpu") -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        model_dir = _resolve_model(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.session = ort.InferenceSession(
            f"{model_dir}/model_quantized.onnx", providers=["CPUExecutionProvider"]
        )
        self.input_names = {item.name for item in self.session.get_inputs()}

    def rank(self, text: str, candidate_texts: list[str], batch_size: int = 16) -> np.ndarray:
        if not candidate_texts:
            return np.empty(0, dtype=np.float32)
        scores = []
        for offset in range(0, len(candidate_texts), batch_size):
            pairs = [(text, candidate) for candidate in candidate_texts[offset:offset + batch_size]]
            encoded = self.tokenizer(
                [pair[0] for pair in pairs], [pair[1] for pair in pairs],
                padding=True, truncation=True, max_length=512, return_tensors="np",
            )
            feeds = {key: value.astype(np.int64) for key, value in encoded.items()
                     if key in self.input_names}
            scores.extend(self.session.run(None, feeds)[0].reshape(-1).tolist())
        return np.asarray(scores, dtype=np.float32)


def representative_text(cluster: Any, max_chars: int = 1200) -> str:
    members = sorted(cluster.members, key=lambda member: member.get("date", ""), reverse=True)
    return "\n".join(member.get("text", "")[:max_chars] for member in members[:3])


def cluster_posts(rows, vectors, reranker, threshold=DEFAULT_COSINE_THRESHOLD, window_hours=24,
                  retrieval_top_k=8, rerank_top_k=8, reranker_batch_size=16,
                  on_progress=None, image_exclude_sources=None,
                  reranker_threshold=DEFAULT_RERANKER_THRESHOLD):
    """Retrieve by cosine, then attach only if the best reranker logit passes.

    Rows must be chronological and aligned with vectors. ``threshold=None`` uses
    the default cosine gate; it does not enable unconditional attachment.
    Thresholds are starting values and need calibration on labeled event pairs.
    """

    threshold = DEFAULT_COSINE_THRESHOLD if threshold is None else threshold
    if not np.isfinite(threshold) or not -1 <= threshold <= 1:
        raise ValueError("Cosine threshold must be finite and between -1 and 1")
    if not np.isfinite(reranker_threshold):
        raise ValueError("Reranker threshold must be a finite raw logit")
    if not np.isfinite(window_hours) or window_hours <= 0 or reranker_batch_size < 1:
        raise ValueError("Time window and reranker batch size must be positive")
    if retrieval_top_k < 1 or rerank_top_k < 1 or rerank_top_k > retrieval_top_k:
        raise ValueError("Require 1 <= rerank_top_k <= retrieval_top_k")
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(rows) or not np.isfinite(vectors).all():
        raise ValueError("Expected one finite embedding per row")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms <= 1e-12):
        raise ValueError("Embeddings must have nonzero norms")
    vectors = vectors / norms
    if any(a["_posted_at"] > b["_posted_at"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Rows and embeddings must be sorted chronologically together")
    clusters = []
    for index, (row, vector) in enumerate(zip(rows, vectors, strict=True), 1):
        active = [c for c in clusters if row["_posted_at"] - c.last_seen_at <= timedelta(hours=window_hours)]
        scored = []
        for cluster in active:
            if str(row["channel"]) in cluster.sources:
                continue
            norm = np.linalg.norm(cluster.sum_vector)
            if norm <= 1e-12:
                continue
            center = cluster.sum_vector / norm
            similarity = float(vector @ center)
            if similarity >= threshold:
                scored.append((similarity, cluster))
        scored.sort(key=lambda item: (-item[0], item[1].event_id))
        candidates = scored[:retrieval_top_k]
        chosen = None
        if candidates:
            eligible = candidates[:rerank_top_k]
            query = row.get("text") or row.get("_clean_text", "")
            scores = np.asarray(reranker.rank(
                query[:2000], [representative_text(c) for _, c in eligible], reranker_batch_size
            ))
            if scores.shape != (len(eligible),) or not np.isfinite(scores).all():
                raise ValueError("Reranker must return one finite logit per candidate")
            best = int(np.argmax(scores))
            if scores[best] >= reranker_threshold:
                chosen = eligible[best][1]
        if chosen is None:
            chosen = EventCluster(len(clusters) + 1, row["_posted_at"], row["_posted_at"],
                                  np.zeros_like(vector), first_vector=vector.copy())
            clusters.append(chosen)
        EventClusterAttach.attach(chosen, row, vector, image_exclude_sources)
        if on_progress:
            on_progress(index, len(rows))
    exported = []
    for c in clusters:
        labels = {}
        for member in c.members:
            for item in member["labels"]:
                labels[item["label"]] = max(labels.get(item["label"], 0), item["score"])
        exported.append({"event_id": c.event_id, "sources": sorted(c.sources),
                         "images": c.images,
                         "labels": [{"label": k, "score": v} for k, v in sorted(labels.items(), key=lambda x: (-x[1], x[0]))[:4]],
                         "members": c.members})
    return exported


class EventClusterAttach:
    @staticmethod
    def attach(cluster, row, vector, image_exclude_sources=None):
        member = {"post_id": row.get("post_id"), "source": str(row["channel"]),
                  "date": row.get("date"), "text": row.get("text", ""),
                  "url": row.get("url"), "images": row.get("images", []),
                  "labels": row.get("predicted_labels", [])}
        cluster.members.append(member)
        if not hasattr(cluster, "images"):
            cluster.images = []
        excluded = CLUSTER_IMAGE_EXCLUDED_SOURCES if image_exclude_sources is None else set(image_exclude_sources)
        for image in row.get("images", []):
            if len(cluster.images) >= 4:
                break
            if image_source_is_excluded(image.get("source") or row.get("channel"), excluded):
                continue
            if not any(image.get("image_id") == existing.get("image_id") or same_image(image, existing)
                       for existing in cluster.images):
                cluster.images.append(dict(image))
        cluster.sources.add(member["source"])
        cluster.sum_vector += vector
        cluster.last_seen_at = row["_posted_at"]
