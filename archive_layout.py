"""
Helpers for the archive/YYYY/MM/DD.md layout: date↔path mapping, neighbor
lookup, and rendering of prev/next markdown navigation links with relative
paths that work from any file in the tree.
"""
from __future__ import annotations

import os
import re
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple, Union

PathLike = Union[str, Path]

_ARCHIVE_RE = re.compile(r"^(\d{4})/(\d{2})/(\d{2})\.md$")

def replace_marker_block(content: str, marker_name: str, new_body: str) -> str:
    """
    Replace the body of every `<!-- {marker_name} -->...<!-- /{marker_name} -->`
    block in `content` with `new_body`. Returns content unchanged if no markers
    are present.
    """
    pattern = re.compile(
        rf"<!-- {re.escape(marker_name)} -->\n.*?\n<!-- /{re.escape(marker_name)} -->",
        re.DOTALL,
    )
    replacement = f"<!-- {marker_name} -->\n{new_body}\n<!-- /{marker_name} -->"
    return pattern.sub(replacement, content)


def replace_all_nav_blocks(content: str, new_nav: str) -> str:
    """Back-compat wrapper around `replace_marker_block(content, "nav", new_nav)`."""
    return replace_marker_block(content, "nav", new_nav)


def inject_nav_blocks(content: str, nav: str) -> str:
    """
    Ensure `content` has top and bottom nav marker blocks holding `nav`.
    If markers already exist, replace their contents. Otherwise insert one
    block after the first H1 line and one before the last `---` separator
    (or at the end if no separator).
    """
    if "<!-- nav -->" in content:
        return replace_all_nav_blocks(content, nav)

    block = f"<!-- nav -->\n{nav}\n<!-- /nav -->"
    lines = content.split("\n")

    out: List[str] = []
    inserted_top = False
    for line in lines:
        out.append(line)
        if not inserted_top and line.startswith("# "):
            out.append("")
            out.append(block)
            inserted_top = True

    last_sep = max(
        (i for i, ln in enumerate(out) if ln.strip() == "---"),
        default=None,
    )
    if last_sep is not None:
        out = out[:last_sep] + [block, ""] + out[last_sep:]
    else:
        out.extend(["", block])
    return "\n".join(out)


def archive_path_for_date(d: date, archive_root: PathLike) -> Path:
    return (
        Path(archive_root)
        / f"{d.year:04d}"
        / f"{d.month:02d}"
        / f"{d.day:02d}.md"
    )


def date_for_archive_path(p: PathLike, archive_root: PathLike) -> Optional[date]:
    try:
        rel = Path(p).relative_to(Path(archive_root))
    except ValueError:
        return None
    m = _ARCHIVE_RE.match(rel.as_posix())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def list_archive_dates(archive_root: PathLike) -> List[date]:
    root = Path(archive_root)
    if not root.is_dir():
        return []
    dates: List[date] = []
    for p in root.rglob("*.md"):
        d = date_for_archive_path(p, root)
        if d is not None:
            dates.append(d)
    return sorted(dates)


def find_neighbors(
    target: date, archive_dates: List[date]
) -> Tuple[Optional[date], Optional[date]]:
    """
    Return (prev, next) — the closest dates strictly before and after `target`
    in `archive_dates`. `target` itself is excluded from both. `archive_dates`
    must be sorted ascending.
    """
    prev: Optional[date] = None
    nxt: Optional[date] = None
    for d in archive_dates:
        if d < target:
            prev = d
        elif d > target:
            nxt = d
            break
    return prev, nxt


def _rel(target: Path, *, from_path: Path) -> str:
    return os.path.relpath(target, start=from_path.parent).replace(os.sep, "/")


def archive_dir_link_for(
    reference_date: Optional[date],
    archive_root: PathLike,
    current_path: PathLike,
) -> str:
    """
    Relative path from `current_path` to the directory containing the archive
    for `reference_date` (i.e. that file's parent month directory). When
    `reference_date` is None, returns a path to the archive root itself. This
    is the link target for "the archive" in the README footer; using the most
    recent archive's parent guarantees the link is non-404 even on the first
    day of a month or year, when today's month directory does not yet exist.
    """
    archive_root = Path(archive_root)
    if reference_date is None:
        target = archive_root
    else:
        target = archive_path_for_date(reference_date, archive_root).parent
    return _rel(target, from_path=Path(current_path))


def render_nav(
    prev_date: Optional[date],
    next_date: Optional[date],
    *,
    current_path: PathLike,
    archive_root: PathLike,
    today_target: Optional[PathLike] = None,
) -> str:
    """
    Render a single line of markdown nav links: `[← YYYY-MM-DD](rel) | [YYYY-MM-DD →](rel)`.
    Either side may be omitted. If `next_date` is None and `today_target` is
    given, a `[Today →](rel)` link is emitted in its place. Returns "" when
    no neighbor and no today_target.
    """
    current = Path(current_path)
    root = Path(archive_root)

    parts: List[str] = []
    if prev_date is not None:
        rel = _rel(archive_path_for_date(prev_date, root), from_path=current)
        parts.append(f"[← {prev_date.isoformat()}]({rel})")
    if next_date is not None:
        rel = _rel(archive_path_for_date(next_date, root), from_path=current)
        parts.append(f"[{next_date.isoformat()} →]({rel})")
    elif today_target is not None:
        rel = _rel(Path(today_target), from_path=current)
        parts.append(f"[Today →]({rel})")

    return " | ".join(parts)
