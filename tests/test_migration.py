import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from migrate_archive_layout import (  # noqa: E402
    execute_migration,
    parse_legacy_archive_filename,
    plan_migration,
)


def test_parse_legacy_filename_extracts_date():
    assert parse_legacy_archive_filename(Path("2026-04-26.md")) == date(2026, 4, 26)


def test_parse_legacy_filename_rejects_non_legacy_names():
    assert parse_legacy_archive_filename(Path("README.md")) is None
    assert parse_legacy_archive_filename(Path("26.md")) is None
    assert parse_legacy_archive_filename(Path("2026-13-01.md")) is None  # invalid month


def test_plan_migration_lists_legacy_files_only(tmp_path):
    (tmp_path / "2026-04-26.md").write_text("a", encoding="utf-8")
    (tmp_path / "2026-04-27.md").write_text("b", encoding="utf-8")
    (tmp_path / "stray.md").write_text("x", encoding="utf-8")
    nested = tmp_path / "2026" / "04"
    nested.mkdir(parents=True)
    (nested / "28.md").write_text("c", encoding="utf-8")
    moves = plan_migration(tmp_path)
    assert sorted(m.archive_date for m in moves) == [
        date(2026, 4, 26),
        date(2026, 4, 27),
    ]


def test_plan_migration_empty_when_root_missing(tmp_path):
    assert plan_migration(tmp_path / "nope") == []


def test_dry_run_makes_no_changes(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "2026-04-26.md").write_text("orig\n", encoding="utf-8")
    moves = execute_migration(
        archive_root=archive,
        readme_path=tmp_path / "README.md",
        dry_run=True,
        log=lambda *a, **kw: None,
    )
    assert len(moves) == 1
    assert (archive / "2026-04-26.md").exists()
    assert not (archive / "2026" / "04" / "26.md").exists()


def test_real_run_moves_files_and_injects_nav(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    readme = tmp_path / "README.md"
    readme.write_text("# README\n", encoding="utf-8")

    (archive / "2026-04-26.md").write_text(
        "# Daily GitHub Activity (2026-04-26)\n"
        "\n"
        "body 26\n"
        "\n"
        "---\n"
        "footer\n",
        encoding="utf-8",
    )
    (archive / "2026-04-27.md").write_text(
        "# Daily GitHub Activity (2026-04-27)\n"
        "\n"
        "body 27\n"
        "\n"
        "---\n"
        "footer\n",
        encoding="utf-8",
    )

    execute_migration(
        archive_root=archive,
        readme_path=readme,
        dry_run=False,
        log=lambda *a, **kw: None,
    )

    a26 = archive / "2026" / "04" / "26.md"
    a27 = archive / "2026" / "04" / "27.md"
    assert a26.exists() and a27.exists()
    assert not (archive / "2026-04-26.md").exists()
    assert not (archive / "2026-04-27.md").exists()

    c26 = a26.read_text(encoding="utf-8")
    # Older file: no prev, next is 04-27
    assert "[2026-04-27 →](27.md)" in c26
    assert "←" not in c26
    assert "body 26" in c26
    assert "footer" in c26

    c27 = a27.read_text(encoding="utf-8")
    # Newest file: prev is 04-26, no next archive → Today fallback
    assert "[← 2026-04-26](26.md)" in c27
    assert "[Today →](../../../README.md)" in c27


def test_real_run_handles_files_already_having_nav_markers(tmp_path):
    """Re-running migration should not duplicate nav blocks."""
    archive = tmp_path / "archive"
    archive.mkdir()
    readme = tmp_path / "README.md"
    readme.write_text("# README\n", encoding="utf-8")
    (archive / "2026-04-26.md").write_text(
        "# Daily GitHub Activity (2026-04-26)\n"
        "\n"
        "<!-- nav -->\nstale\n<!-- /nav -->\n"
        "\n"
        "body\n"
        "\n"
        "<!-- nav -->\nstale\n<!-- /nav -->\n"
        "\n"
        "---\n"
        "footer\n",
        encoding="utf-8",
    )
    execute_migration(
        archive_root=archive,
        readme_path=readme,
        dry_run=False,
        log=lambda *a, **kw: None,
    )
    out = (archive / "2026" / "04" / "26.md").read_text(encoding="utf-8")
    assert out.count("<!-- nav -->") == 2  # not duplicated
    assert "stale" not in out
