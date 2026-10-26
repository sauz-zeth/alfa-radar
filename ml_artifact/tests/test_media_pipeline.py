from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from ml_artifact.core.build_business_news_html import build_html
from ml_artifact.core.ingest import parse_sources, stable_id
from ml_artifact.core.news_cluster_reranker import cluster_posts
from ml_artifact.core.image_utils import image_source_is_excluded


class StubReranker:
    def rank(self, text, candidates, batch_size=16):
        return np.arange(len(candidates), dtype=np.float32)


class MediaPipelineTests(unittest.TestCase):
    def test_catalogs_and_stable_rss_id(self):
        feeds = parse_sources()
        self.assertGreaterEqual(len(feeds), 90)
        self.assertEqual(stable_id("x", "y"), stable_id("x", "y"))

    def test_cluster_keeps_four_unique_images(self):
        rows = []
        hashes = ["0000000000000000", "ffffffffffffffff", "0f0f0f0f0f0f0f0f",
                  "f0f0f0f0f0f0f0f0", "00ff00ff00ff00ff", "ff00ff00ff00ff00"]
        for index in range(6):
            rows.append({
                "post_id": f"source/{index}", "channel": str(index), "date": "2026-10-25T00:00:00Z",
                "text": "text", "_clean_text": "text",
                "_posted_at": datetime(2026, 10, 25, tzinfo=UTC), "predicted_labels": [],
                "images": [{"image_id": "duplicate", "path": "/tmp/a.jpg", "source": str(index),
                            "post_id": f"source/{index}", "sha256": "same", "perceptual_hash": "0" * 16}]
                           + [{"image_id": f"unique-{index}", "path": f"/tmp/{index}.jpg", "source": str(index),
                               "post_id": f"source/{index}", "sha256": str(index), "perceptual_hash": hashes[index]}],
            })
        result = cluster_posts(rows, np.ones((6, 2), dtype=np.float32), StubReranker(), threshold=0.99)[0]
        self.assertEqual(len(result["images"]), 4)
        self.assertEqual(len({item["image_id"] for item in result["images"]}), 4)

    def test_cluster_can_exclude_image_source(self):
        row = {"post_id": "rss/1", "channel": "RSS News", "date": "2026-10-25T00:00:00Z",
               "text": "text", "_clean_text": "text", "_posted_at": datetime(2026, 10, 25, tzinfo=UTC),
               "predicted_labels": [], "images": [{"image_id": "x", "path": "/tmp/x.jpg",
               "source": "RSS News", "sha256": "x", "perceptual_hash": "0" * 16}]}
        result = cluster_posts([row], np.ones((1, 2), dtype=np.float32), StubReranker(),
                               image_exclude_sources=["rss news"])[0]
        self.assertEqual(result["images"], [])

    def test_catalogue_image_exclusions_match_display_and_slug_names(self):
        self.assertTrue(image_source_is_excluded("Кошелёк Onlíner"))
        self.assertTrue(image_source_is_excluded("ALTA.ru — логистика"))
        self.assertTrue(image_source_is_excluded("drom.ru — новости"))
        self.assertTrue(image_source_is_excluded("хабр_лучшее_за_неделю"))
        self.assertFalse(image_source_is_excluded("ТАСС"))

    def test_html_contains_cluster_images(self):
        payload = {"profiles": [{"uid": "U", "activity": "demo", "category_impacts": {}, "selected_sources": []}],
                   "recommendations": [{"uid": "U", "clusters": [{"event_id": 1, "members": [], "images": [{"path": "/tmp/a.jpg", "source": "rss"}], "sources": []}]}],
                   "scoring": {}, "metrics": None}
        html = build_html(payload, {"accounts": []})
        self.assertIn("cluster-images", html)
        self.assertIn("imageSrc", html)


if __name__ == "__main__":
    unittest.main()
