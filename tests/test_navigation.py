from datetime import date

from daily_github_activity.archive_layout import (
    archive_path_for_date,
    find_neighbors,
    render_nav,
)


def test_find_neighbors_with_gaps():
    dates = [date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 10)]
    assert find_neighbors(date(2026, 1, 5), dates) == (
        date(2026, 1, 1),
        date(2026, 1, 10),
    )


def test_find_neighbors_first_has_no_prev():
    dates = [date(2026, 1, 1), date(2026, 1, 5)]
    assert find_neighbors(date(2026, 1, 1), dates) == (None, date(2026, 1, 5))


def test_find_neighbors_last_has_no_next():
    dates = [date(2026, 1, 1), date(2026, 1, 5)]
    assert find_neighbors(date(2026, 1, 5), dates) == (date(2026, 1, 1), None)


def test_find_neighbors_target_not_in_list_returns_surrounding_pair():
    dates = [date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 10)]
    assert find_neighbors(date(2026, 1, 7), dates) == (
        date(2026, 1, 5),
        date(2026, 1, 10),
    )


def test_find_neighbors_target_after_all_archives():
    dates = [date(2026, 1, 1), date(2026, 1, 5)]
    assert find_neighbors(date(2026, 1, 7), dates) == (date(2026, 1, 5), None)


def test_find_neighbors_empty_archive_list():
    assert find_neighbors(date(2026, 1, 1), []) == (None, None)


def test_render_nav_archive_with_both_neighbors_same_month(tmp_path):
    current = archive_path_for_date(date(2026, 4, 27), tmp_path)
    nav = render_nav(
        prev_date=date(2026, 4, 26),
        next_date=date(2026, 4, 28),
        current_path=current,
        archive_root=tmp_path,
    )
    assert nav == "[← 2026-04-26](26.md) | [2026-04-28 →](28.md)"


def test_render_nav_cross_month(tmp_path):
    current = archive_path_for_date(date(2026, 4, 1), tmp_path)
    nav = render_nav(
        prev_date=date(2026, 3, 31),
        next_date=date(2026, 4, 2),
        current_path=current,
        archive_root=tmp_path,
    )
    assert "[← 2026-03-31](../03/31.md)" in nav
    assert "[2026-04-02 →](02.md)" in nav


def test_render_nav_cross_year(tmp_path):
    current = archive_path_for_date(date(2026, 1, 1), tmp_path)
    nav = render_nav(
        prev_date=date(2025, 12, 31),
        next_date=None,
        current_path=current,
        archive_root=tmp_path,
    )
    assert nav == "[← 2025-12-31](../../2025/12/31.md)"


def test_render_nav_archive_falls_back_to_today_when_no_next(tmp_path):
    archive_root = tmp_path / "archive"
    readme = tmp_path / "README.md"
    current = archive_path_for_date(date(2026, 4, 27), archive_root)
    nav = render_nav(
        prev_date=date(2026, 4, 26),
        next_date=None,
        current_path=current,
        archive_root=archive_root,
        today_target=readme,
    )
    assert "[← 2026-04-26](26.md)" in nav
    assert "[Today →](../../../README.md)" in nav


def test_render_nav_for_readme_links_to_most_recent_archive(tmp_path):
    archive_root = tmp_path / "archive"
    archive_root.mkdir()
    readme = tmp_path / "README.md"
    nav = render_nav(
        prev_date=date(2026, 4, 26),
        next_date=None,
        current_path=readme,
        archive_root=archive_root,
    )
    assert nav == "[← 2026-04-26](archive/2026/04/26.md)"


def test_render_nav_empty_when_no_neighbors_and_no_today_target(tmp_path):
    current = archive_path_for_date(date(2026, 4, 27), tmp_path)
    assert (
        render_nav(
            prev_date=None,
            next_date=None,
            current_path=current,
            archive_root=tmp_path,
        )
        == ""
    )


def test_render_nav_only_prev(tmp_path):
    current = archive_path_for_date(date(2026, 4, 27), tmp_path)
    nav = render_nav(
        prev_date=date(2026, 4, 26),
        next_date=None,
        current_path=current,
        archive_root=tmp_path,
    )
    assert nav == "[← 2026-04-26](26.md)"


def test_render_nav_only_next(tmp_path):
    current = archive_path_for_date(date(2026, 4, 27), tmp_path)
    nav = render_nav(
        prev_date=None,
        next_date=date(2026, 4, 28),
        current_path=current,
        archive_root=tmp_path,
    )
    assert nav == "[2026-04-28 →](28.md)"
