"""The offline artifact package must not depend on backend ORM modules."""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def test_artifact_package_imports_without_orm() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import ml_artifact.core.pipeline; "
            "import ml_artifact.core.image_utils; "
            "assert not any(name == 'back.db' or name.startswith('back.db.') "
            "for name in sys.modules)",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )


def test_normalized_post_from_record_preserves_raw_payload() -> None:
    from ml_pipeline.contracts import NormalizedPost

    published_at = datetime(2026, 10, 26, tzinfo=UTC)
    post = NormalizedPost.from_record(
        {
            "id": "post-1",
            "source_name": "Example",
            "title": "Title",
            "text": "Body",
            "published_at": published_at,
            "raw": {"profile_id": "profile-1"},
            "media": [{"image_id": "image-1"}],
        }
    )

    assert post.post_id == "post-1"
    assert post.published_at == published_at
    assert post.raw == {"profile_id": "profile-1"}
    assert post.media == ({"image_id": "image-1"},)
