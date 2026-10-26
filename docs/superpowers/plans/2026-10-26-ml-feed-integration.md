# ML Feed Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Connect the real ML clustering and per-profile analysis pipeline to the asynchronous news feed while preserving Telegram/RSS collection and the NewsEvent API contract.

**Architecture:** Ingest stores source posts and media in PostgreSQL/shared storage and returns immediately. A separate ml_pipeline worker leases posts, runs classification, embedding, clustering, and profile analysis, then updates one cluster-level NewsEvent and one EventAnalysis per active profile. The API exposes those records and the frontend computes the final importance score.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy async, Alembic, PostgreSQL locks, existing ruBERT/BGE-M3/reranker code, existing LLM abstraction, React/TypeScript/Zod, Bun, Playwright, Docker Compose.

**Spec:** docs/superpowers/specs/2026-10-26-ml-feed-integration-design.md

## Global Constraints

- Rename ml/ to ml_artifact/ without losing contents; runtime code belongs in ml_pipeline/.
- NewsEvent is cluster-level; profile-specific status, impact, and score components belong to EventAnalysis.
- ML_FEED_THRESHOLD=30; primary results use I > 30, weak results use I < 30 and are capped at 10.
- Use FOR UPDATE SKIP LOCKED plus leases for posts and a PostgreSQL advisory lock for cluster mutation.
- Media files live in a shared volume; PostgreSQL stores normalized metadata, checksums, perceptual hashes, and relative paths.
- A bad image never rejects its text post. Excluded image sources remain cluster members and count toward independent sources.
- No automatic historical re-clustering, separate cluster table, or event-per-profile records.
- Direct influence calls final Kimi; indirect influence calls Qwen screening and then Kimi only when related.

---

### Task 1: Move artifacts and define runtime boundaries

Files:
- Move ml/ to ml_artifact/
- Create ml_pipeline/__init__.py, contracts.py, adapter.py
- Modify ml_artifact README, pipeline, CLI, core imports, and tests
- Test ml_artifact/tests/test_import_paths.py

Interfaces:
- NormalizedPost.from_record(post: Mapping[str, Any]) -> NormalizedPost
- classify_post(post: NormalizedPost, classifier: PostClassifier) -> ClassificationDecision
- Adapter modules consume plain mappings/dataclasses and never import SQLAlchemy.

- [ ] Write the failing import test:

~~~python
def test_artifact_package_imports_without_orm() -> None:
    import ml_artifact.core.pipeline
    import ml_artifact.core.image_utils
    assert "back.db" not in ml_artifact.core.pipeline.__dict__
~~~

- [ ] Run cd ml_artifact && uv run pytest -q tests/test_import_paths.py; expect failure because the package has not moved.
- [ ] Run git mv ml ml_artifact; update package-relative imports, CLI/model paths, documentation, and add the runtime package/contracts.
- [ ] Run cd ml_artifact && uv run pytest -q; expect pass.
- [ ] Commit: git add ml_artifact ml_pipeline && git commit -m "refactor: separate ml artifacts from runtime pipeline".

### Task 2: Add persistence fields and migration

Files:
- Modify back/src/back/db/models.py classes NewsEvent, EventAnalysis, and Post
- Create back/migrations/versions/new_ml_feed_runtime_fields.py
- Test back/tests/test_models_migration.py

Interfaces:
- Post adds media, attempt_count, lease_until, last_error, and status_updated_at.
- NewsEvent adds media.
- EventAnalysis adds status, impact, related, direct, fact, within_month, why, card_text, key_facts, bank_position, and independent_source_count.

- [ ] Write tests asserting JSON defaults, retry fields, all analysis columns, and migration upgrade/downgrade.
- [ ] Run cd back && uv run pytest -q tests/test_models_migration.py; expect failure because columns are absent.
- [ ] Add SQLAlchemy fields and Alembic upgrade/downgrade with JSONB defaults, nullable lease/error columns, timestamps, and indexes on status plus lease_until, news_event_id, and cluster_key.
- [ ] Run cd back && uv run alembic upgrade head && uv run pytest -q tests/test_models_migration.py; expect pass.
- [ ] Commit the model, migration, and test changes.

### Task 3: Make ingest asynchronous and persist media

Files:
- Create back/src/back/services/media.py
- Modify back/src/back/api/routes/ingest.py, schemas/ingest.py, services/pipeline.py, config.py, and back/.env.example
- Test back/tests/test_ingest_media.py and the ingest cases in test_api_mockup.py

Interfaces:
- save_post_media(files: Sequence[UploadFile], source_name: str, post_id: UUID) -> list[dict[str, Any]]
- POST /api/ingest/posts accepts a JSON payload plus optional multipart image files, creates a received/received Post, and does not call ingest_from_profile.

- [ ] Write tests for multipart acceptance, atomic media metadata, immediate response, and a broken image that leaves the text post stored.
- [ ] Run the focused ingest tests; expect failure because the endpoint is JSON-only and synchronous.
- [ ] Implement MEDIA_ROOT, temporary-file-plus-replace writes, SHA-256/perceptual hash/dimensions, per-file error capture, and one transaction for post plus metadata. Preserve profile_id in Post.raw without restricting worker analysis.
- [ ] Run the focused ingest tests; expect pass.
- [ ] Commit the endpoint, storage, schema, config, and tests.

### Task 4: Forward Telegram and RSS media

Files:
- Modify tg-ingest payload.py, backend.py, main.py
- Modify back services/rss.py and rss_poller.py
- Test tg-ingest payload/backend tests and back/tests/test_rss.py

Interfaces:
- build_payload accepts optional image metadata.
- send_post accepts image byte tuples and sends multipart form data.
- RSS items expose images from enclosures, thumbnails, content, and Open Graph fallback.

- [ ] Write failing tests for Telegram image metadata, multipart forwarding, RSS media extraction, Open Graph fallback, and image-download failure tolerance.
- [ ] Run tg-ingest and RSS tests; expect failure on the new cases.
- [ ] Implement per-image exception handling, multipart requests, RSS namespace parsing, and Open Graph fallback without changing text/link/date behavior.
- [ ] Run both suites; expect pass.
- [ ] Commit the collector changes.

### Task 5: Implement adapter and exact LLM routing

Files:
- Create ml_pipeline/adapter.py, llm_routes.py, and their tests
- Reuse/modify ml_artifact/core/news_cluster_reranker.py and image_utils.py

Interfaces:
- classify_post drops text under 40 characters, no-label posts, and Реклама/мусор; valid posts use first 1200 characters and a normalized 1024-dimensional embedding.
- merge_cluster_event(existing, post, cluster_key) -> ClusterEventPatch max-aggregates labels, appends source posts, and deduplicates at most four images by image id/SHA-256/perceptual hash while filtering only image display.
- route_profile_analysis(cluster, profile, llm) -> ProfileAnalysisResult implements direct Kimi and indirect Qwen screening followed by conditional Kimi.

- [ ] Write unit tests for filters, media mapping, aggregation, excluded-source behavior, and direct/indirect routing.
- [ ] Run cd ml_pipeline && uv run pytest -q; expect failure because contracts are absent.
- [ ] Implement pure functions using cosine 0.78, top-8 candidates, raw reranker logit >= 0.0; keep ORM/session code out.
- [ ] Run the adapter suite; expect pass without network calls.
- [ ] Commit the adapter and routing modules.

### Task 6: Implement leased worker and transactional clustering

Files:
- Create ml_pipeline/repository.py, worker.py, cli.py
- Test back/tests/test_worker_repository.py and ml_pipeline/tests/test_worker.py

Interfaces:
- PostRepository.claim_batch(limit: int, lease_seconds: int) -> list[PostRecord]
- mark_retry(post_id, error), mark_failed(post_id, error), mark_clustered(post_id, event_id, cluster_key)
- Worker.run() -> None
- process_post(session, post, adapter, settings) -> None

- [ ] Write tests for SKIP LOCKED, expired lease reclaim, retry/failed limits, idempotent resume after news_event_id, and advisory-lock concurrency.
- [ ] Run both worker test files; expect failure because repository/worker modules are absent.
- [ ] Implement chronological processing, 24-hour active-cluster selection, same-channel exclusion, pg_advisory_xact_lock(hashtext(cluster_key)), atomic event updates, active-profile analysis upserts, exponential backoff, and graceful SIGTERM shutdown.
- [ ] Run both focused suites; expect pass without external model or LLM calls.
- [ ] Commit the worker changes.

### Task 7: Expose profile-specific feed analysis

Files:
- Modify back API/routes/feed.py, services/feed.py, schemas/feed.py, and schemas/insights.py
- Test back/tests/test_feed.py and test_feed_personalization.py

Interfaces:
- event_to_feed_item(..., analysis: EventAnalysis | None, ...) -> FeedItem
- Feed output adds related, direct, fact, within_month, and independent_source_count; common facts and sources remain from NewsEvent.

- [ ] Add tests proving two profiles receive different statuses/components for one event, unmatched categories skip analysis, weak events remain in API output, and source counts honor subscriptions/source groups.
- [ ] Run the focused feed tests; expect failure because the route does not join the new fields.
- [ ] Join current-profile EventAnalysis, calculate normalized independent source groups, preserve the old fallback only when all new components exist, and stop server-side filtering of weak events.
- [ ] Run the focused feed suite; expect pass.
- [ ] Commit the feed route, service, schema, and test changes.

### Task 8: Rank and render the personalized feed

Files:
- Create front/src/feed/ranking.ts and ranking tests
- Modify front API feed schema, feed mapper/types/screens, and front/playwright.test.ts

Interfaces:
- importanceScore(item: FeedItem) = 40*related + 25*direct + 20*fact + 15*within_month
- rankFeed(items: FeedItem[], threshold = 30) sorts primary by score and weak items by independent source count, then publication date descending, with a ten-item weak cap.

- [ ] Write TypeScript tests for score calculation, primary ordering, weak cap, and date tie-breaks; add Playwright fixtures for allowed and excluded image sources.
- [ ] Run the ranking test; expect failure because helpers and fields are absent.
- [ ] Add Zod fields, implement ranking before presentation mapping, remove decayed rank_score sorting, and keep fallback photos/text cards for old or excluded-media records.
- [ ] Run bun test, bun run build, and bun run test:visual; expect pass.
- [ ] Commit the frontend changes.

### Task 9: Package the worker and document operations

Files:
- Modify back config and env example, docker-compose.yml, back/Dockerfile, root README, docs/DEPLOY.md, back/README.md, and tg-ingest/README.md
- Create ml_pipeline/Dockerfile, pyproject.toml, and config tests

Interfaces:
- Settings include ML_WORKER_ENABLED, polling interval, batch size, lease timeout, max attempts, ML_FEED_THRESHOLD=30, artifact/model paths, media root, and LLM model paths.
- Compose adds ml-worker sharing PostgreSQL, model, and media volumes; it receives no Telegram credentials.
- Worker starts with python -m ml_pipeline.worker, runs Alembic before polling, and handles SIGTERM.

- [ ] Write config tests for threshold 30, positive lease/batch/attempt defaults, and disabled-worker behavior.
- [ ] Run the config tests; expect failure because settings/package files are absent.
- [ ] Implement packaging, Compose environment/volumes, startup wiring, env documentation, media backup instructions, and the explicit historical re-clustering boundary.
- [ ] Run docker compose config, worker config tests, and back ruff; expect pass.
- [ ] Commit the packaging and documentation.

### Task 10: Run full verification and review scope

- [ ] Run cd back && uv run pytest -q && uv run ruff check .
- [ ] Run the tg-ingest, ml_artifact, and ml_pipeline pytest suites.
- [ ] Run cd front && bun run build && bun run test:visual.
- [ ] Run Alembic upgrade head, docker compose config, and a disposable docker compose up --build smoke run. Confirm API, worker, and collectors share PostgreSQL/media volumes and worker has no Telegram session.
- [ ] Run git diff --check and git status --short. Verify excluded media, weak-event API visibility, profile-specific ordering, retry/failed persistence, no historical re-clustering, and no staged secrets/caches/generated outputs.
