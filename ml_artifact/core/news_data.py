"""Data preparation shared by the final clustering pipeline and explorer."""
from __future__ import annotations
import json
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import numpy as np
AD_LABEL = "Реклама/мусор"
URL_RE = re.compile(r"https?://\S+|t\.me/\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]+")
SPACE_RE = re.compile(r"\s+")


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)

def clean_text(value: str) -> str:
    value = URL_RE.sub(" ", value)
    value = MENTION_RE.sub(" ", value)
    return SPACE_RE.sub(" ", value).strip()

def load_slice(raw_dir: Path, start: datetime, end: datetime) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    invalid_dates = 0
    for path in sorted(raw_dir.glob("*.jsonl")):
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    row = json.loads(line)
                    posted_at = parse_datetime(row["date"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    invalid_dates += 1
                    continue
                if start <= posted_at < end:
                    row["_posted_at"] = posted_at
                    row["_clean_text"] = clean_text(row.get("text") or "")
                    records.append(row)
    records.sort(key=lambda row: (row["_posted_at"], row.get("post_id", "")))
    return records, invalid_dates

def predict_in_batches(
    classifier: RubertOnnxClassifier,
    records: list[dict[str, Any]],
    batch_size: int,
    timing: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    eligible = [row for row in records if len(row["_clean_text"]) >= 40]
    short_count = len(records) - len(eligible)
    predictions: list[dict[str, Any]] = [
        {
            "post_id": row.get("post_id"),
            "channel": row.get("channel"),
            "date": row.get("date"),
            "status": "short_or_empty",
            "labels": [],
        }
        for row in records
        if len(row["_clean_text"]) < 40
    ]
    retained: list[dict[str, Any]] = []
    no_label_count = ad_count = 0
    batch_count = (len(eligible) + batch_size - 1) // batch_size

    for offset in range(0, len(eligible), batch_size):
        batch = eligible[offset : offset + batch_size]
        started = time.perf_counter()
        batch_predictions = classifier.predict([row["_clean_text"] for row in batch])
        elapsed = time.perf_counter() - started
        if timing is not None:
            lengths = [len(row["_clean_text"]) for row in batch]
            timing.append({"batch_size": len(batch), "elapsed_seconds": elapsed,
                           "avg_chars": sum(lengths) / len(lengths),
                           "min_chars": min(lengths), "max_chars": max(lengths)})
        for row, prediction in zip(batch, batch_predictions, strict=True):
            labels = prediction["labels"]
            label_names = [item["label"] for item in labels]
            status = "kept"
            if not labels:
                status = "no_labels"
                no_label_count += 1
            elif AD_LABEL in label_names:
                status = "ad_or_spam"
                ad_count += 1
            else:
                row["predicted_labels"] = labels
                retained.append(row)

            predictions.append(
                {
                    "post_id": row.get("post_id"),
                    "channel": row.get("channel"),
                    "date": row.get("date"),
                    "status": status,
                    "labels": labels,
                }
            )
        completed = offset // batch_size + 1
        if completed % 10 == 0 or completed == batch_count:
            print(
                f"ruBERT batches: {completed}/{batch_count} "
                f"({min(offset + len(batch), len(eligible))}/{len(eligible)} posts)",
                flush=True,
            )

    return retained, {
        "short_or_empty": short_count,
        "no_labels": no_label_count,
        "ad_or_spam": ad_count,
        "retained": len(retained),
        "classified": len(eligible),
    }, predictions

def load_predictions(
    records: list[dict[str, Any]], path: Path
) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    predictions = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_post_id = {row.get("post_id"): row for row in predictions}
    retained: list[dict[str, Any]] = []
    counts = {"short_or_empty": 0, "no_labels": 0, "ad_or_spam": 0, "retained": 0, "classified": 0}
    for record in records:
        prediction = by_post_id.get(record.get("post_id"))
        if prediction is None:
            raise ValueError(f"Prediction is missing for {record.get('post_id')}")
        status = prediction.get("status")
        if status == "short_or_empty":
            counts["short_or_empty"] += 1
        elif status == "no_labels":
            counts["no_labels"] += 1
            counts["classified"] += 1
        elif status == "ad_or_spam":
            counts["ad_or_spam"] += 1
            counts["classified"] += 1
        elif status == "kept":
            counts["retained"] += 1
            counts["classified"] += 1
            record["predicted_labels"] = prediction.get("labels", [])
            retained.append(record)
        else:
            raise ValueError(f"Unknown prediction status {status!r} for {record.get('post_id')}")
    return retained, counts, predictions

@dataclass
class EventCluster:
    event_id: int
    created_at: datetime
    last_seen_at: datetime
    sum_vector: np.ndarray
    first_vector: np.ndarray | None = None
    members: list[dict[str, Any]] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)
    images: list[dict[str, Any]] = field(default_factory=list)

    @property
    def mean_vector(self) -> np.ndarray:
        return self.sum_vector / len(self.members)

def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
