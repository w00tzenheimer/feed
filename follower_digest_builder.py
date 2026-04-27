"""Compatibility shim — invokes daily_github_activity.digest.main().

Kept at the repo root so the GitHub Actions workflow can continue to call
`python follower_digest_builder.py` without modification. Prefer `pip install
.` followed by the `follower-digest` console script for ad-hoc use.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running from a fresh checkout without `pip install`.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from daily_github_activity.digest import main  # noqa: E402

if __name__ == "__main__":
    main()
