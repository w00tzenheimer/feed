from datetime import date

from daily_github_activity.archive_layout import archive_dir_link_for, archive_path_for_date


def test_steady_state_links_to_current_month(tmp_path):
    """Mid-month: prev archive's parent dir IS the current month."""
    archive_root = tmp_path / "archive"
    readme = tmp_path / "README.md"
    link = archive_dir_link_for(
        reference_date=date(2026, 4, 26),
        archive_root=archive_root,
        current_path=readme,
    )
    assert link == "archive/2026/04"


def test_first_of_month_falls_back_to_previous_month(tmp_path):
    """On Apr 1, no archives in 04/ yet — most recent is 2026-03-31."""
    archive_root = tmp_path / "archive"
    readme = tmp_path / "README.md"
    link = archive_dir_link_for(
        reference_date=date(2026, 3, 31),
        archive_root=archive_root,
        current_path=readme,
    )
    assert link == "archive/2026/03"


def test_first_of_year_falls_back_to_previous_years_december(tmp_path):
    archive_root = tmp_path / "archive"
    readme = tmp_path / "README.md"
    link = archive_dir_link_for(
        reference_date=date(2026, 12, 31),
        archive_root=archive_root,
        current_path=readme,
    )
    assert link == "archive/2026/12"


def test_no_archives_links_to_archive_root(tmp_path):
    archive_root = tmp_path / "archive"
    readme = tmp_path / "README.md"
    link = archive_dir_link_for(
        reference_date=None,
        archive_root=archive_root,
        current_path=readme,
    )
    assert link == "archive"


def test_link_from_archive_file_perspective_is_dot(tmp_path):
    """An archive at archive/2026/04/27.md linking to its own month dir → `.`."""
    archive_root = tmp_path / "archive"
    current = archive_path_for_date(date(2026, 4, 27), archive_root)
    link = archive_dir_link_for(
        reference_date=date(2026, 4, 27),
        archive_root=archive_root,
        current_path=current,
    )
    assert link == "."


def test_link_from_archive_file_to_previous_month_dir(tmp_path):
    """Archive at archive/2026/04/01.md linking to archive/2026/03/ → `../03`."""
    archive_root = tmp_path / "archive"
    current = archive_path_for_date(date(2026, 4, 1), archive_root)
    link = archive_dir_link_for(
        reference_date=date(2026, 3, 31),
        archive_root=archive_root,
        current_path=current,
    )
    assert link == "../03"
