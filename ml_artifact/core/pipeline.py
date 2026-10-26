"""ruBERT filtering → BGE-M3 INT8 → top-8 candidates → INT8 reranker."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np

try:
    from .image_utils import normalize_image_source
except ImportError:
    from image_utils import normalize_image_source

if __package__:
    from .news_data import load_slice, load_predictions, predict_in_batches, parse_datetime, write_jsonl
    from .news_cluster_reranker import (EMBEDDING_MODEL, RERANKER_MODEL, DEFAULT_COSINE_THRESHOLD,
                                      DEFAULT_RERANKER_THRESHOLD, OnnxEmbedder, LocalReranker, cluster_posts)
    from .cluster_report import export_html
else:
    from news_data import load_slice, load_predictions, predict_in_batches, parse_datetime, write_jsonl
    from news_cluster_reranker import (EMBEDDING_MODEL, RERANKER_MODEL, DEFAULT_COSINE_THRESHOLD,
                                     DEFAULT_RERANKER_THRESHOLD, OnnxEmbedder, LocalReranker, cluster_posts)
    from cluster_report import export_html

FINAL = Path(__file__).resolve().parent
ROOT = FINAL.parent


def get_vectors(rows, model_name, cache_dir, chars=1200, batch_size=16):
    """Cache normalized CLS embeddings with the explorer's fingerprint format."""
    texts = [r['_clean_text'][:chars] if chars else r['_clean_text'] for r in rows]
    # Keep existing notebook caches reusable after relocating the same model.
    identity = 'skatzR/USER-BGE-M3-ONNX-INT8' if Path(model_name).resolve() == Path(EMBEDDING_MODEL) else str(model_name)
    fingerprint = hashlib.sha256(json.dumps(
        {'model': identity, 'pooling': 'cls-int8-v2', 'chars': chars,
         'items': [(r['post_id'], t) for r, t in zip(rows, texts, strict=True)]},
        ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f'embeddings_{fingerprint}.npz'
    if cache.exists():
        with np.load(cache, allow_pickle=False) as saved:
            vectors = saved['vectors']
        print(f'Эмбеддинги из кеша: {cache.name}', flush=True)
    else:
        embedder = OnnxEmbedder(model_name)
        batch_count = (len(texts) + batch_size - 1) // batch_size
        chunks = []
        for offset in range(0, len(texts), batch_size):
            batch_number = offset // batch_size + 1
            chunks.append(embedder.encode(texts[offset:offset + batch_size], batch_size=batch_size))
            if batch_number % 10 == 0 or batch_number == batch_count:
                print(f'BGE batches: {batch_number}/{batch_count} '
                      f'({min(offset + batch_size, len(texts))}/{len(texts)} posts)', flush=True)
        vectors = np.concatenate(chunks) if chunks else np.empty((0, 1024), dtype=np.float32)
        np.savez_compressed(cache, vectors=vectors)
    if vectors.ndim != 2 or vectors.shape[0] != len(rows) or not np.isfinite(vectors).all():
        raise ValueError(f'Некорректный кеш эмбеддингов: {cache}')
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-3):
        raise ValueError('Эмбеддинги должны быть нормированы')
    return vectors


def run_pipeline(*, raw_dir=ROOT / 'data/raw', output_dir=ROOT / 'outputs/cluster_explorer',
                 predictions=None, start='2025-10-22T00:00:00Z', end='2025-10-24T00:00:00Z',
                 model_dir=ROOT / 'models' / 'rubert_int4', embedding_model=EMBEDDING_MODEL,
                 reranker_model=RERANKER_MODEL, cosine_threshold=DEFAULT_COSINE_THRESHOLD, window_hours=24,
                 embedding_chars=1200, embedding_batch_size=16, reranker_candidates=8,
                 reranker_batch_size=8, classifier_batch_size=16, write_html=True,
                 image_exclude_sources=None, reranker_threshold=DEFAULT_RERANKER_THRESHOLD):
    start, end = parse_datetime(start), parse_datetime(end)
    if end <= start:
        raise ValueError('end must be after start')
    if window_hours <= 0 or embedding_chars < 0:
        raise ValueError('Invalid time window or text length')
    if min(embedding_batch_size, reranker_candidates, reranker_batch_size, classifier_batch_size) < 1:
        raise ValueError('Batch sizes and candidate count must be positive')
    cosine_threshold = DEFAULT_COSINE_THRESHOLD if cosine_threshold is None else cosine_threshold
    if not np.isfinite(cosine_threshold) or not -1 <= cosine_threshold <= 1:
        raise ValueError('Cosine threshold must be finite and between -1 and 1')
    if not np.isfinite(reranker_threshold):
        raise ValueError('Reranker threshold must be a finite raw logit')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Pipeline] читаю корпус: {raw_dir}", flush=True)
    rows, invalid_dates = load_slice(Path(raw_dir), start, end)
    raw_count = len(rows)
    print(f"[Pipeline] загружено новостей: {raw_count}", flush=True)
    inference_timings = []
    prediction_path = Path(predictions) if predictions is not None else output_dir / 'predictions.jsonl'
    if prediction_path.exists():
        print(f"[ruBERT] использую кеш предсказаний: {prediction_path}", flush=True)
        rows, counts, _ = load_predictions(rows, prediction_path)
    else:
        if __package__:
            from .onnx_rubert_classifier import RubertOnnxClassifier
        else:
            from onnx_rubert_classifier import RubertOnnxClassifier
        print(f"[ruBERT] загружаю модель: {model_dir}", flush=True)
        classifier = RubertOnnxClassifier(model_dir)
        print("[ruBERT] модель загружена, начинаю инференс", flush=True)
        rows, counts, predicted = predict_in_batches(classifier, rows, classifier_batch_size,
                                                     timing=inference_timings)
        prediction_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(prediction_path, predicted)
    if not rows:
        raise ValueError('Нет новостей после фильтрации ruBERT')
    print(f"[BGE] строю эмбеддинги для {len(rows)} новостей", flush=True)
    vectors = get_vectors(rows, embedding_model, output_dir, embedding_chars, embedding_batch_size)
    print("[BGE] эмбеддинги готовы", flush=True)
    print(f"[Reranker] загружаю модель: {reranker_model}", flush=True)
    reranker = LocalReranker(reranker_model)
    print("[Reranker] модель загружена, начинаю кластеризацию", flush=True)
    started = time.perf_counter()

    def progress(done, total):
        if done % 100 == 0 or done == total:
            elapsed = time.perf_counter() - started
            rate = done / elapsed if elapsed > 0 else 0.0
            print(f'[Reranker] {done}/{total} новостей; '
                  f'{elapsed:.1f} с, {rate:.1f} нов./с', flush=True)

    clusters = cluster_posts(rows, vectors, reranker, threshold=cosine_threshold,
                             reranker_threshold=reranker_threshold,
                             window_hours=window_hours, retrieval_top_k=reranker_candidates,
                             rerank_top_k=reranker_candidates, reranker_batch_size=reranker_batch_size,
                             on_progress=progress, image_exclude_sources=image_exclude_sources)
    parameters = dict(embedding_model=str(embedding_model), reranker_model=str(reranker_model),
                      matching="thresholded_top_k_rerank", window_hours=window_hours,
                      cosine_threshold=cosine_threshold, reranker_threshold=reranker_threshold,
                      reranker_score_type="raw_logit",
                      retrieval_top_k=reranker_candidates, rerank_top_k=reranker_candidates,
                      embedding_chars=embedding_chars, embedding_batch_size=embedding_batch_size,
                      reranker_batch_size=reranker_batch_size, filter_counts=counts,
                      raw_records=raw_count, clustered_records=sum(len(cluster.get('members', [])) for cluster in clusters),
                      clusters_count=len(clusters),
                      inference_cpu=inference_timings,
                      start=start.isoformat(), end_exclusive=end.isoformat(),
                      image_policy={"max_per_cluster": 4, "dedup": "sha256+phash", "phash_distance": 8},
                      image_exclude_sources=[normalize_image_source(s) for s in (image_exclude_sources or [])],
                      seconds=round(time.perf_counter()-started, 2), invalid_dates=invalid_dates)
    result = {'parameters': parameters, 'clusters': clusters}
    (output_dir / 'clusters.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Plain list for the existing business selection/ranking scripts.
    (output_dir / 'news_clusters.json').write_text(json.dumps(clusters, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if write_html:
        export_html(output_dir / 'clusters_browser.html', clusters, parameters)
    print(f'Готово: {len(rows)} новостей → {len(clusters)} кластеров; {output_dir}', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/cluster_explorer')
    parser.add_argument('--predictions', type=Path, help='Reuse predictions, or save new predictions to this path')
    parser.add_argument('--start', default='2025-10-22T00:00:00Z')
    parser.add_argument('--end', default='2025-10-24T00:00:00Z', help='Exclusive end in UTC')
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'models' / 'rubert_int4')
    parser.add_argument('--embedding-model', default=EMBEDDING_MODEL, help='Local model directory')
    parser.add_argument('--reranker-model', default=RERANKER_MODEL, help='Local model directory')
    parser.add_argument('--cosine-threshold', type=float, default=DEFAULT_COSINE_THRESHOLD,
                        help='Minimum cosine similarity for a cluster candidate')
    parser.add_argument('--reranker-threshold', type=float, default=DEFAULT_RERANKER_THRESHOLD,
                        help='Minimum raw reranker logit to attach a post')
    parser.add_argument('--window-hours', type=float, default=24)
    parser.add_argument('--embedding-chars', type=int, default=1200)
    parser.add_argument('--embedding-batch-size', type=int, default=16)
    parser.add_argument('--reranker-candidates', type=int, default=8)
    parser.add_argument('--reranker-batch-size', type=int, default=8)
    parser.add_argument('--classifier-batch-size', type=int, default=16)
    parser.add_argument('--no-html', dest='write_html', action='store_false')
    run_pipeline(**vars(parser.parse_args()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
