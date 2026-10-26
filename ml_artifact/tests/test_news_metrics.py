import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ml_artifact.core.news_metrics import build_metrics, render_metrics, summarize_cpu_inference, usage_metrics
from ml_artifact.core.rank_business_news import LLMClient, relation_importance, validate_assessment


def event(request_id='request-1', **overrides):
    return dict(request_id=request_id, event_id=1, source='api', model='test/model',
                stage='qwen_direct', outcome='success', duration_seconds=2,
                tokens={'input': 10, 'output': 5, 'total': 15},
                cost={'amount': .1, 'currency': 'TEST', 'source': 'api'}, **overrides)


def record(history=None, **telemetry):
    return dict(event_id=1, status='feed', impact='прямое', sources=2,
                members=[{}, {}], importance=40, assessment={'ok': True},
                telemetry={'analysis_requests': history or [], **telemetry})


class MetricsTests(unittest.TestCase):
    def test_relation_importance_uses_four_flags(self):
        relation = {'why': [{'highlight': '2%', 'text': 'рост ставки повышает стоимость финансирования'}, {'highlight': 'кредиты', 'text': 'подорожают и увеличат издержки компании'}], 'related': True, 'direct': True,
                    'fact': True, 'within_month': True}
        self.assertEqual(relation_importance(relation), 100)
        relation['within_month'] = False
        self.assertEqual(relation_importance(relation), 85)

    def test_unrelated_relation_forces_zero_and_rejects_other_flags(self):
        relation = {'why': [{'highlight': 'нет связи', 'text': 'с профилем компании'}, {'highlight': 'нет данных', 'text': 'для оценки влияния'}], 'related': False, 'direct': False,
                    'fact': False, 'within_month': False}
        self.assertEqual(relation_importance(relation), 0)
        relation['fact'] = True
        with self.assertRaises(ValueError):
            validate_assessment(relation)

    def test_resume_keeps_original_cost_separate_from_current_run(self):
        metrics = build_metrics([record([event()], resumed=True)], [], 1, 1)
        self.assertEqual(metrics['current_run']['api_calls'], 0)
        self.assertEqual(metrics['result_analysis']['tokens']['total']['known_sum'], 15)
        self.assertEqual(metrics['result_analysis']['costs'][0]['amount'], .1)
        self.assertEqual(metrics['resumed_events'], 1)
        self.assertIn('Исходный анализ результатов · включая сохранённые вызовы', render_metrics(metrics))

    def test_history_deduplicates_requests_across_results(self):
        second = {**record([event()]), 'event_id': 2}
        metrics = build_metrics([record([event()]), second], [], 1, 2)
        self.assertEqual(metrics['result_analysis']['api_calls'], 1)

    def test_funnel_preserves_corpus_company_and_limit_scopes(self):
        metrics = build_metrics([record()], [], 1, 3, funnel={
            'raw_news': 100, 'clustered_news': 80, 'clusters': 60,
            'company_publications': 20, 'company_clusters': 10})
        funnel = metrics['funnel']
        self.assertEqual(funnel['clusters'], 60)
        self.assertEqual(funnel['company_clusters'], 10)
        self.assertEqual(funnel['requested_clusters'], 3)
        self.assertEqual(funnel['processed_clusters'], 1)
        self.assertEqual(funnel['processed_publications'], 2)
        self.assertEqual(funnel['feed_publications'], 2)
        self.assertEqual(metrics['remaining'], 2)
        html = render_metrics(metrics)
        self.assertIn('Исходный корпус: сырых публикаций / после ruBERT / после кластеризации', html)
        self.assertIn('LLM обработано событий / публикаций', html)

    def test_missing_telemetry_stays_unknown_instead_of_zero_measurement(self):
        metrics = build_metrics([record()], [], 1, 1)
        self.assertEqual(metrics['historical_metrics_missing_events'], 1)
        self.assertIn('История расходов и токенов неполная', render_metrics(metrics))
        self.assertIn('Время CPU-инференса ruBERT: нет измерений', render_metrics(metrics))
        self.assertNotIn('clusters', metrics['funnel'])

    def test_partial_legacy_cache_history_is_marked_missing(self):
        metrics = build_metrics([record([event()], historical_metrics_missing=True)], [], 1, 1)
        self.assertEqual(metrics['historical_metrics_missing_events'], 1)

    def test_failed_event_and_unknown_usage(self):
        failed = event()
        failed.update(outcome='network_error', tokens={}, cost=None)
        metrics = build_metrics([{**record([failed]), 'status': 'error'}], [failed], 1, 4)
        self.assertEqual(metrics['failed'], 1)
        self.assertEqual(metrics['completed'], 0)
        self.assertEqual(metrics['remaining'], 3)
        self.assertFalse(metrics['current_run']['tokens']['total']['complete'])
        self.assertEqual(metrics['current_run']['cost_unknown_calls'], 1)

    def test_fractional_average_length_does_not_drop_cpu_samples(self):
        metrics = summarize_cpu_inference([{'batch_size': 2, 'elapsed_seconds': 4, 'avg_chars': 256.5}])
        self.assertEqual(metrics['queries'], 2)
        self.assertEqual(sum(b['n'] for b in metrics['by_length'].values()), 2)
        self.assertEqual(metrics['by_length']['257-512']['mean'], 2)
        self.assertEqual(metrics['batch_elapsed_seconds']['sum'], 4)

    def test_reasoning_tokens_are_not_added_twice(self):
        usage = usage_metrics({'usage': {'prompt_tokens': 10, 'completion_tokens': 5,
                              'completion_tokens_details': {'reasoning_tokens': 3}}}, 'test')
        self.assertEqual(usage['tokens']['total'], 15)
        self.assertIsNone(usage['cost'])

    def test_api_retry_and_disk_cache_preserve_actual_usage(self):
        def response(content):
            return io.BytesIO(json.dumps({'choices': [{'message': {'content': content}}],
                'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'cost': .1}}).encode())
        with TemporaryDirectory() as temp:
            client = LLMClient('fake-key', Path(temp), attempts=2)
            client.event_id = 1
            with (patch('ml_artifact.core.rank_business_news.urlopen', side_effect=[response('invalid json'), response('{}')]) as request,
                  patch('ml_artifact.core.rank_business_news.time.sleep')):
                client.ask('test', 'task', {}, lambda answer: None)
            self.assertEqual(request.call_count, 2)
            first = build_metrics([record(client.analysis_events)], client.events, 1, 1)
            self.assertEqual(first['current_run']['failed_calls'], 1)
            self.assertEqual(first['current_run']['retries'], 1)
            self.assertEqual(first['current_run']['tokens']['total']['known_sum'], 30)
            self.assertAlmostEqual(first['current_run']['costs'][0]['amount'], .2)
            cached = LLMClient('fake-key', Path(temp))
            cached.event_id = 1
            with patch('ml_artifact.core.rank_business_news.urlopen') as request:
                cached.ask('test', 'task', {}, lambda answer: None)
            request.assert_not_called()
            second = build_metrics([record(cached.analysis_events)], cached.events, 1, 1)
            self.assertEqual(second['current_run']['cache_hits'], 1)
            self.assertEqual(second['current_run']['api_calls'], 0)
            self.assertEqual(second['result_analysis']['tokens']['total']['known_sum'], 30)


if __name__ == '__main__':
    unittest.main()
