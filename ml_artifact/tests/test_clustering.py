from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from ml_artifact.core.news_cluster_reranker import cluster_posts
from ml_artifact.core.pipeline import main, run_pipeline


class Reranker:
    def __init__(self, score=3.0):
        self.score = score
        self.calls = []

    def rank(self, text, candidates, batch_size=16):
        self.calls.append(candidates)
        return np.full(len(candidates), self.score)


def row(index, *, hour=0, source=None):
    dt = datetime(2026, 10, 25, tzinfo=UTC) + timedelta(hours=hour)
    text = f"Новость {index}: текст для проверки кластеризации событий."
    return dict(post_id=str(index), channel=source or str(index), date=dt.isoformat(),
                _posted_at=dt, text=text, _clean_text=text, predicted_labels=[])


class ClusteringTests(unittest.TestCase):
    def test_unrelated_posts_create_new_events_without_reranking(self):
        ranker = Reranker(100)
        result = cluster_posts([row(0), row(1)], np.eye(2), ranker)
        self.assertEqual(len(result), 2)
        self.assertEqual(ranker.calls, [])

    def test_reranker_can_reject_the_only_candidate(self):
        ranker = Reranker(-10)
        result = cluster_posts([row(0), row(1)], np.ones((2, 2)), ranker)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(ranker.calls), 1)

    def test_similar_posts_join_and_normalize_input(self):
        result = cluster_posts([row(0), row(1)], [[2, 0], [5, 0]], Reranker())
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['members']), 2)

    def test_explicit_cosine_threshold_changes_membership(self):
        vectors = [[1, 0], [.8, .6]]
        for threshold, count in [(.79, 1), (.81, 2), (None, 1)]:
            with self.subTest(threshold=threshold):
                self.assertEqual(len(cluster_posts([row(0), row(1)], vectors, Reranker(),
                                                  threshold=threshold)), count)

    def test_explicit_reranker_threshold_is_raw_logit(self):
        result = cluster_posts([row(0), row(1)], np.ones((2, 2)), Reranker(2),
                               reranker_threshold=3)
        self.assertEqual(len(result), 2)

    def test_time_window_and_existing_source_exclude_candidates(self):
        for second in [row(1, hour=25), row(1, source='0')]:
            ranker = Reranker()
            self.assertEqual(len(cluster_posts([row(0), second], np.ones((2, 2)), ranker)), 2)
            self.assertEqual(ranker.calls, [])

    def test_unsorted_rows_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'chronologically'):
            cluster_posts([row(0, hour=2), row(1)], np.ones((2, 2)), Reranker())

    def test_invalid_embeddings_fail_before_reranking(self):
        for vectors in [np.ones((1, 2)), np.zeros((2, 2)), [[1, 0], [np.nan, 1]]]:
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                cluster_posts([row(0), row(1)], vectors, Reranker())

    def test_invalid_reranker_output_is_rejected(self):
        for scores in [np.array([np.nan]), np.array([]), np.ones((1, 1))]:
            ranker = Reranker()
            with patch.object(ranker, 'rank', return_value=scores), self.assertRaises(ValueError):
                cluster_posts([row(0), row(1)], np.ones((2, 2)), ranker)

    def test_reranker_selects_best_of_top_candidates(self):
        rows = [row(0, source='seed'), row(1, source='seed'), row(2)]
        vectors = [[1, 0], [.8, .6], [1, 0]]
        ranker = Reranker()
        with patch.object(ranker, 'rank', return_value=np.array([1., 4.])):
            result = cluster_posts(rows, vectors, ranker)
        self.assertEqual([m['post_id'] for m in result[1]['members']], ['1', '2'])

    def test_pipeline_uses_thresholds_and_writes_metadata(self):
        rows = [row(0), row(1)]
        with TemporaryDirectory() as temp:
            prediction_path = Path(temp) / 'predictions.jsonl'
            prediction_path.write_text('')
            with (patch('ml_artifact.core.pipeline.load_slice', return_value=(rows, 0)),
                  patch('ml_artifact.core.pipeline.load_predictions', return_value=(rows, {}, [])),
                  patch('ml_artifact.core.pipeline.get_vectors', return_value=np.array([[1, 0], [.8, .6]])),
                  patch('ml_artifact.core.pipeline.LocalReranker', return_value=Reranker(2))):
                result = run_pipeline(output_dir=temp, predictions=prediction_path,
                                      cosine_threshold=.81, reranker_threshold=3,
                                      reranker_candidates=10, write_html=False)
            self.assertEqual(len(result['clusters']), 2)
            self.assertEqual(result['parameters']['cosine_threshold'], .81)
            self.assertEqual(result['parameters']['reranker_threshold'], 3)
            self.assertEqual(json.loads((Path(temp) / 'news_clusters.json').read_text()), result['clusters'])

    def test_cli_defaults_are_valid(self):
        with patch('sys.argv', ['pipeline']), patch('ml_artifact.core.pipeline.run_pipeline') as run:
            main()
        self.assertEqual(run.call_args.kwargs['reranker_candidates'], 8)
        self.assertEqual(run.call_args.kwargs['cosine_threshold'], .78)


if __name__ == '__main__':
    unittest.main()
