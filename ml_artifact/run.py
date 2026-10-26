"""Единый конвейер: ruBERT -> кластеризация -> отбор -> LLM-ранжирование."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:
    from .core.pipeline import run_pipeline
    from .core.ingest import ingest
    from .core.news_cluster_reranker import DEFAULT_COSINE_THRESHOLD, DEFAULT_RERANKER_THRESHOLD
except ImportError:
    from core.pipeline import run_pipeline
    from core.ingest import ingest
    from core.news_cluster_reranker import DEFAULT_COSINE_THRESHOLD, DEFAULT_RERANKER_THRESHOLD


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", required=True, help="UID компании для финального LLM-анализа")
    parser.add_argument("--accounts", type=Path, default=ROOT / "reference_uids.json")
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/pipeline")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--ingest", action="store_true", help="Собрать публикации из RSS перед обработкой")
    parser.add_argument("--dry-run", action="store_true", help="Остановиться перед вызовами LLM")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--cosine-threshold", type=float, default=DEFAULT_COSINE_THRESHOLD)
    parser.add_argument("--reranker-threshold", type=float, default=DEFAULT_RERANKER_THRESHOLD,
                        help="Минимальный raw logit reranker для присоединения к кластеру")
    parser.add_argument("--reranker-candidates", type=int, default=8)
    parser.add_argument("--window-hours", type=float, default=24)
    args, extra = parser.parse_known_args()

    end = datetime.fromisoformat(args.end.replace("Z", "+00:00")) if args.end else datetime.now(UTC)
    start = datetime.fromisoformat(args.start.replace("Z", "+00:00")) if args.start else end - timedelta(hours=48)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    ingest_root = args.output_dir
    if args.ingest:
        ingest(ingest_root, start, end)
        raw_dir = ingest_root / "data" / "raw"
    else:
        raw_dir = args.raw_dir or ROOT / "data/raw"
    cluster_dir = args.output_dir / "clusters"
    run_pipeline(raw_dir=raw_dir, output_dir=cluster_dir, start=start.isoformat(), end=end.isoformat(),
                 cosine_threshold=args.cosine_threshold, reranker_threshold=args.reranker_threshold,
                 reranker_candidates=args.reranker_candidates, window_hours=args.window_hours)

    select_cmd = [sys.executable, "-m", "core.select_business_news",
                  "--accounts", str(args.accounts),
                  "--clusters", str(cluster_dir / "clusters.json"),
                  "--output", str(args.output_dir / "candidates.json")]
    subprocess.run(select_cmd, cwd=ROOT, check=True)

    rank_cmd = [sys.executable, "-m", "core.rank_business_news", "--uid", args.uid,
                "--accounts", str(args.accounts),
                "--clusters", str(cluster_dir / "clusters.json"),
                "--output-dir", str(args.output_dir / "ranking")]
    if args.dry_run:
        rank_cmd.append("--dry-run")
    if args.limit is not None:
        rank_cmd += ["--limit", str(args.limit)]
    rank_cmd += extra
    subprocess.run(rank_cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
