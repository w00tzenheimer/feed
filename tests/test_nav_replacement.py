from daily_github_activity.archive_layout import inject_nav_blocks, replace_all_nav_blocks


def test_replaces_both_top_and_bottom_blocks():
    content = (
        "# Title\n"
        "\n"
        "<!-- nav -->\n"
        "old top\n"
        "<!-- /nav -->\n"
        "\n"
        "body\n"
        "\n"
        "<!-- nav -->\n"
        "old bottom\n"
        "<!-- /nav -->\n"
        "\n"
        "footer\n"
    )
    out = replace_all_nav_blocks(content, "NEW")
    assert "old top" not in out
    assert "old bottom" not in out
    assert out.count("<!-- nav -->\nNEW\n<!-- /nav -->") == 2
    assert "# Title" in out
    assert "footer" in out


def test_no_op_when_markers_absent():
    content = "# Title\n\nbody\n"
    assert replace_all_nav_blocks(content, "NEW") == content


def test_handles_empty_replacement():
    content = "<!-- nav -->\nold\n<!-- /nav -->\n"
    assert replace_all_nav_blocks(content, "") == "<!-- nav -->\n\n<!-- /nav -->\n"


def test_does_not_match_across_separate_blocks():
    """Regex must be non-greedy: two adjacent blocks should be treated separately."""
    content = (
        "<!-- nav -->\nA\n<!-- /nav -->\nmid\n<!-- nav -->\nB\n<!-- /nav -->\n"
    )
    out = replace_all_nav_blocks(content, "X")
    assert "A" not in out
    assert "B" not in out
    assert "mid" in out
    assert out.count("<!-- nav -->\nX\n<!-- /nav -->") == 2


def test_inject_replaces_when_markers_already_present():
    content = "<!-- nav -->\nold\n<!-- /nav -->\nbody\n"
    out = inject_nav_blocks(content, "NEW")
    assert "old" not in out
    assert "<!-- nav -->\nNEW\n<!-- /nav -->" in out
    assert "body" in out


def test_inject_adds_top_block_after_h1():
    content = (
        "# Daily GitHub Activity (2026-04-26)\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "## Today's Activity\n"
        "\n"
        "events here\n"
        "\n"
        "---\n"
        "*footer*\n"
    )
    out = inject_nav_blocks(content, "NAV")
    # Top block sits between H1 and the intro paragraph
    h1_idx = out.index("# Daily GitHub Activity")
    intro_idx = out.index("Intro paragraph.")
    top_marker_idx = out.index("<!-- nav -->")
    assert h1_idx < top_marker_idx < intro_idx
    # Two distinct blocks total
    assert out.count("<!-- nav -->") == 2
    assert out.count("<!-- /nav -->") == 2


def test_inject_adds_bottom_block_before_final_separator():
    content = (
        "# Title\n\nbody\n\n---\n*footer*\n"
    )
    out = inject_nav_blocks(content, "NAV")
    sep_idx = out.rfind("\n---\n")
    bottom_marker_idx = out.rfind("<!-- nav -->")
    assert bottom_marker_idx < sep_idx
    # Footer must remain at the end after the separator
    assert out.endswith("*footer*\n")


def test_inject_appends_block_when_no_separator_present():
    content = "# Title\n\nbody\n"
    out = inject_nav_blocks(content, "NAV")
    # Two blocks (top after H1, bottom appended)
    assert out.count("<!-- nav -->\nNAV\n<!-- /nav -->") == 2
