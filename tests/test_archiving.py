from follower_digest_builder import GitHubDigest


def _readme_with_markers(yesterday: str, body: str = "events go here") -> str:
    return (
        f"# Daily GitHub Activity ({yesterday})\n"
        "\n"
        "<!-- nav -->\n"
        "[← 2026-04-25](archive/2026/04/25.md)\n"
        "<!-- /nav -->\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "## Today's Activity\n"
        "\n"
        f"{body}\n"
        "\n"
        "<!-- nav -->\n"
        "[← 2026-04-25](archive/2026/04/25.md)\n"
        "<!-- /nav -->\n"
        "\n"
        "---\n"
        "*Last updated at 2026-04-26 23:00:00 UTC*\n"
        "<!-- archive-link -->\n"
        "*Historical records are stored in the [`archive`](archive/2026/04) directory.*\n"
        "<!-- /archive-link -->\n"
    )


def _make_digest(tmp_path):
    return GitHubDigest(
        github_token="x",
        github_username="x",
        archive_dir=str(tmp_path / "archive"),
        readme_file=str(tmp_path / "README.md"),
        custom_users_file=str(tmp_path / "no_such_file.txt"),
    )


def test_writes_to_nested_path_with_archive_perspective_nav(tmp_path):
    archive_root = tmp_path / "archive"
    prev = archive_root / "2026" / "04" / "25.md"
    prev.parent.mkdir(parents=True)
    prev.write_text(
        "# Daily GitHub Activity (2026-04-25)\n"
        "\n"
        "<!-- nav -->\n"
        "[Today →](../../../README.md)\n"
        "<!-- /nav -->\n"
        "\n"
        "old events\n"
        "\n"
        "<!-- nav -->\n"
        "[Today →](../../../README.md)\n"
        "<!-- /nav -->\n",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(_readme_with_markers("2026-04-26"), encoding="utf-8")
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")

    new = archive_root / "2026" / "04" / "26.md"
    assert new.exists()
    content = new.read_text(encoding="utf-8")
    # First line preserved
    assert content.startswith("# Daily GitHub Activity (2026-04-26)")
    # Nav rewritten from archive's perspective
    assert "[← 2026-04-25](25.md)" in content
    assert "[Today →](../../../README.md)" in content
    # Original README-relative link is gone
    assert "archive/2026/04/25.md" not in content


def test_updates_previous_archives_next_link_to_point_at_new_file(tmp_path):
    archive_root = tmp_path / "archive"
    prev = archive_root / "2026" / "04" / "25.md"
    prev.parent.mkdir(parents=True)
    prev.write_text(
        "# 2026-04-25\n\n"
        "<!-- nav -->\n[Today →](../../../README.md)\n<!-- /nav -->\n"
        "\nbody\n\n"
        "<!-- nav -->\n[Today →](../../../README.md)\n<!-- /nav -->\n",
        encoding="utf-8",
    )

    (tmp_path / "README.md").write_text(_readme_with_markers("2026-04-26"), encoding="utf-8")
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")

    updated = prev.read_text(encoding="utf-8")
    assert "[Today →]" not in updated
    assert updated.count("[2026-04-26 →](26.md)") == 2  # both top and bottom


def test_no_archive_when_first_line_date_does_not_match_yesterday(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Daily GitHub Activity (2026-04-27)\n\n"
        "<!-- nav -->\n\n<!-- /nav -->\n",
        encoding="utf-8",
    )
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")
    assert not (tmp_path / "archive" / "2026" / "04" / "26.md").exists()


def test_legacy_readme_without_markers_gets_nav_injected(tmp_path):
    """Pre-migration READMEs lack nav markers — injection adds them on archive."""
    legacy = "# Daily GitHub Activity (2026-04-26)\n\nold body\n\n---\nfooter\n"
    (tmp_path / "README.md").write_text(legacy, encoding="utf-8")
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")
    archived = tmp_path / "archive" / "2026" / "04" / "26.md"
    out = archived.read_text(encoding="utf-8")
    # Original body preserved
    assert "old body" in out
    assert "footer" in out
    # Nav blocks injected with Today fallback (no prev archive in this test)
    assert out.count("<!-- nav -->") == 2
    assert "[Today →](../../../README.md)" in out


def test_archive_link_in_footer_is_rewritten_for_archives_perspective(tmp_path):
    """When archived, the [`archive`](...) link is recomputed relative to the archive file."""
    (tmp_path / "README.md").write_text(_readme_with_markers("2026-04-26"), encoding="utf-8")
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")
    new = tmp_path / "archive" / "2026" / "04" / "26.md"
    content = new.read_text(encoding="utf-8")
    # Archive at archive/2026/04/26.md links to its own month dir as `.`
    assert "[`archive`](.)" in content
    # Original README-perspective link must be gone
    assert "[`archive`](archive/2026/04)" not in content


def test_no_previous_archive_means_no_prev_link_in_new_archive(tmp_path):
    (tmp_path / "README.md").write_text(_readme_with_markers("2026-04-26"), encoding="utf-8")
    _make_digest(tmp_path).archive_if_yesterday("2026-04-26")
    new = tmp_path / "archive" / "2026" / "04" / "26.md"
    content = new.read_text(encoding="utf-8")
    # Only "Today →" should appear; no prev arrow
    assert "[Today →](../../../README.md)" in content
    assert "←" not in content
