from datetime import date

from archive_layout import (
    archive_path_for_date,
    date_for_archive_path,
    list_archive_dates,
)


def test_archive_path_nests_year_month_day(tmp_path):
    assert archive_path_for_date(date(2026, 4, 27), tmp_path) == (
        tmp_path / "2026" / "04" / "27.md"
    )


def test_archive_path_zero_pads_month_and_day(tmp_path):
    assert archive_path_for_date(date(2026, 1, 5), tmp_path) == (
        tmp_path / "2026" / "01" / "05.md"
    )


def test_date_for_archive_path_round_trips(tmp_path):
    d = date(2025, 12, 31)
    assert date_for_archive_path(archive_path_for_date(d, tmp_path), tmp_path) == d


def test_date_for_archive_path_returns_none_for_unrelated_paths(tmp_path):
    assert date_for_archive_path(tmp_path / "README.md", tmp_path) is None
    assert (
        date_for_archive_path(tmp_path / "2026" / "stray.md", tmp_path) is None
    )
    assert (
        date_for_archive_path(tmp_path / "2026" / "13" / "01.md", tmp_path) is None
    )


def _seed(root, dates):
    for d in dates:
        p = archive_path_for_date(d, root)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("seed", encoding="utf-8")


def test_list_archive_dates_returns_sorted_ascending(tmp_path):
    _seed(tmp_path, [date(2026, 1, 3), date(2025, 12, 31), date(2026, 2, 1)])
    assert list_archive_dates(tmp_path) == [
        date(2025, 12, 31),
        date(2026, 1, 3),
        date(2026, 2, 1),
    ]


def test_list_archive_dates_ignores_non_archive_files(tmp_path):
    (tmp_path / "stray.md").write_text("x")
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "loose.md").write_text("x")
    _seed(tmp_path, [date(2026, 1, 1)])
    assert list_archive_dates(tmp_path) == [date(2026, 1, 1)]


def test_list_archive_dates_returns_empty_when_root_missing(tmp_path):
    assert list_archive_dates(tmp_path / "does_not_exist") == []
