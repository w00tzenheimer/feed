"""
One-shot migration: archive/YYYY-MM-DD.md → archive/YYYY/MM/DD.md.

After moving each legacy file into its nested location, refreshes the
top/bottom nav blocks in every archive so prev/next links resolve under the
new layout. Idempotent: re-running on an already-migrated tree just
re-renders the nav (no duplicate markers, no spurious moves).
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Callable, List, NamedTuple, Optional

# Allow running this script from a fresh checkout without `pip install`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from daily_github_activity.archive_layout import (  # noqa: E402
    archive_path_for_date,
    find_neighbors,
    inject_nav_blocks,
    list_archive_dates,
    render_nav,
)

_LEGACY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.md$")


class Move(NamedTuple):
    old: Path
    new: Path
    archive_date: date


def parse_legacy_archive_filename(path: Path) -> Optional[date]:
    m = _LEGACY_RE.match(path.name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def plan_migration(archive_root: Path) -> List[Move]:
    if not archive_root.is_dir():
        return []
    moves: List[Move] = []
    for path in sorted(archive_root.iterdir()):
        if not path.is_file():
            continue
        d = parse_legacy_archive_filename(path)
        if d is None:
            continue
        moves.append(
            Move(old=path, new=archive_path_for_date(d, archive_root), archive_date=d)
        )
    return moves


def execute_migration(
    archive_root: Path,
    readme_path: Path,
    *,
    dry_run: bool,
    log: Callable[..., None] = print,
) -> List[Move]:
    moves = plan_migration(archive_root)
    if moves:
        log(f"Planned {len(moves)} moves:")
        for m in moves:
            log(f"  {m.old.relative_to(archive_root)} → {m.new.relative_to(archive_root)}")
    else:
        log("No legacy archive files found.")

    if dry_run:
        log("Dry run — no files moved, no nav rewritten.")
        return moves

    for m in moves:
        m.new.parent.mkdir(parents=True, exist_ok=True)
        m.old.rename(m.new)

    final_dates = list_archive_dates(archive_root)
    log(f"Refreshing nav for {len(final_dates)} archive files...")
    for d in final_dates:
        path = archive_path_for_date(d, archive_root)
        prev, nxt = find_neighbors(d, final_dates)
        nav = render_nav(
            prev_date=prev,
            next_date=nxt,
            current_path=path,
            archive_root=archive_root,
            today_target=readme_path if nxt is None else None,
        )
        original = path.read_text(encoding="utf-8")
        updated = inject_nav_blocks(original, nav)
        if updated != original:
            path.write_text(updated, encoding="utf-8")

    log(f"Done. Moved {len(moves)} files; refreshed nav for {len(final_dates)}.")
    return moves


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate archive/ to archive/YYYY/MM/DD.md layout and refresh nav links."
    )
    parser.add_argument("--archive-dir", default="archive", help="Archive root (default: archive)")
    parser.add_argument("--readme-file", default="README.md", help="README path used for 'Today →' fallback link")
    parser.add_argument("--dry-run", action="store_true", help="Show planned moves without changing files")
    args = parser.parse_args()

    execute_migration(
        archive_root=Path(args.archive_dir),
        readme_path=Path(args.readme_file),
        dry_run=args.dry_run,
        log=print,
    )


if __name__ == "__main__":
    main()
