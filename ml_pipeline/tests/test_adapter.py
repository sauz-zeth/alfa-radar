from __future__ import annotations

from ml_pipeline.adapter import classify_post, merge_cluster_event
from ml_pipeline.contracts import NormalizedPost


class Classifier:
    def __init__(self, labels):
        self.labels = labels
        self.seen = ""

    def predict(self, texts):
        self.seen = texts[0]
        return [{"labels": self.labels}]

    def embed(self, text):
        return [3.0] + [0.0] * 1023


def test_classify_post_filters_short_empty_and_ad_posts():
    classifier = Classifier([{"label": "ok", "score": 0.9}])
    assert classify_post(NormalizedPost("1", "x", "short"), classifier).status == "ignored"
    classifier.labels = []
    assert classify_post(NormalizedPost("2", "x", "a" * 50), classifier).status == "ignored"
    classifier.labels = [{"label": "Реклама/мусор", "score": 1.0}]
    assert classify_post(NormalizedPost("3", "x", "a" * 50), classifier).status == "ignored"


def test_classify_post_truncates_and_normalizes_embedding():
    classifier = Classifier([{"label": "Экономика", "score": 0.9}])
    decision = classify_post(NormalizedPost("1", "x", "  " + "a" * 1500), classifier)
    assert decision.status == "accepted"
    assert len(classifier.seen) == 1200
    assert len(decision.embedding) == 1024
    assert decision.embedding[0] == 1.0


def test_merge_preserves_sources_but_excludes_media_and_deduplicates():
    media = tuple(
        {"image_id": str(i), "sha256": str(i), "perceptual_hash": f"{i:016x}", "source": "ТАСС"}
        for i in range(5)
    )
    post = NormalizedPost(
        "2", "Интерфакс", "another source", labels=({"id": 4, "score": 0.7},), media=media
    )
    patch = merge_cluster_event(
        {"category_ids": [4], "source_posts": [{"post_id": "1", "source": "ТАСС"}], "media": []},
        post,
        "cluster",
    )
    assert patch.cluster_key == "cluster"
    assert len(patch.source_posts) == 2
    assert patch.source_posts[-1]["source"] == "Интерфакс"
    assert len(patch.media) == 4


def test_merge_is_idempotent_for_existing_post_and_image():
    post = NormalizedPost("1", "ТАСС", "text", media=({"image_id": "a"},))
    patch = merge_cluster_event(
        {"source_posts": [{"post_id": "1"}], "media": [{"image_id": "a"}]}, post, "k"
    )
    assert len(patch.source_posts) == 1
    assert len(patch.media) == 1
