from daily_github_activity.digest import load_custom_usernames, merge_logins


def test_load_returns_empty_list_when_file_missing(tmp_path):
    assert load_custom_usernames(tmp_path / "missing.txt") == []


def test_load_strips_full_line_comments_and_blanks(tmp_path):
    p = tmp_path / "custom.txt"
    p.write_text(
        "# header comment\n"
        "\n"
        "alice\n"
        "  # indented comment\n"
        "bob\n"
        "\n",
        encoding="utf-8",
    )
    assert load_custom_usernames(p) == ["alice", "bob"]


def test_load_strips_leading_at_sign(tmp_path):
    p = tmp_path / "custom.txt"
    p.write_text("@alice\n@bob\ncarol\n", encoding="utf-8")
    assert load_custom_usernames(p) == ["alice", "bob", "carol"]


def test_load_strips_surrounding_whitespace(tmp_path):
    p = tmp_path / "custom.txt"
    p.write_text("  alice  \n\t@bob\n", encoding="utf-8")
    assert load_custom_usernames(p) == ["alice", "bob"]


def test_load_dedupes_within_file_preserving_first_occurrence(tmp_path):
    p = tmp_path / "custom.txt"
    p.write_text("alice\nbob\nalice\n", encoding="utf-8")
    assert load_custom_usernames(p) == ["alice", "bob"]


def test_merge_logins_preserves_order_followed_first():
    assert merge_logins(["alice", "bob"], ["carol", "dave"]) == [
        "alice",
        "bob",
        "carol",
        "dave",
    ]


def test_merge_logins_dedupes_across_lists():
    assert merge_logins(["alice", "bob"], ["bob", "carol"]) == [
        "alice",
        "bob",
        "carol",
    ]


def test_merge_logins_handles_empty_inputs():
    assert merge_logins([], []) == []
    assert merge_logins(["alice"], []) == ["alice"]
    assert merge_logins([], ["alice"]) == ["alice"]
