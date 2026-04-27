# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Python tool (`follower_digest_builder.py`) that regenerates `README.md` with the day's public GitHub activity (Watch/Fork/Create-repo/Public events) from every user `GITHUB_REPOSITORY_OWNER` follows, plus any extra logins listed in `custom_users.txt`. GitHub Actions runs it hourly via `.github/workflows/daily_digest.yml` and commits the refreshed README, the `archive/` tree, and `custom_users.txt` back to `main`. There is no service, no DB, no web app — the rendered README *is* the product.

Pure helpers used by both the runtime and the migration script live in `archive_layout.py`. Tests are in `tests/`. One-shot tooling lives in `scripts/`.

## Commands

```bash
pip install .                              # runtime (PyGithub)
pip install -e ".[dev]"                    # adds pytest/black/mypy
pytest                                     # 49 tests, ~0.3s

# Run digest locally — defaults to env vars for creds
GITHUB_TOKEN=... GITHUB_REPOSITORY_OWNER=<handle> python follower_digest_builder.py

# Useful local-iteration flags (don't clobber real README/archive)
python follower_digest_builder.py \
  --readme-file /tmp/README.md \
  --archive-dir /tmp/archive \
  --custom-users-file /tmp/custom_users.txt \
  --log-level DEBUG

# One-shot archive layout migration (idempotent — can re-run safely)
python scripts/migrate_archive_layout.py --dry-run
python scripts/migrate_archive_layout.py
```

## Architecture notes (non-obvious)

- **Archival is README-driven, not date-driven.** `archive_if_yesterday` reads the *first line* of the existing `README.md`, regex-extracts a `(YYYY-MM-DD)` date, and only archives if it equals "yesterday" (UTC). If the README has been regenerated multiple times the same day, nothing is archived. If the first line gets reformatted such that `FIRST_LINE_DATE_PATTERN` no longer matches, archives silently stop. Preserve the `# Daily GitHub Activity (YYYY-MM-DD)` first-line shape in any template change.
- **"Today" is UTC.** All date comparisons use `datetime.now(datetime.timezone.utc).date()`. Don't switch to local time — the workflow runs hourly on `cron: '0 * * * *'` and would skew the day boundary.
- **Archive layout is `archive/YYYY/MM/DD.md`.** `archive_layout.archive_path_for_date` is the only place that constructs these paths — go through it. The 106 pre-existing flat files were migrated by `scripts/migrate_archive_layout.py`.
- **Nav links use `<!-- nav -->...<!-- /nav -->` markers.** Every README and every archive carries two of these blocks (top, bottom) holding the same `[← prev](rel) | [next →](rel)` line. Markers exist so an existing archive can be rewritten in place without parsing markdown.
- **The previous most-recent archive is rewritten on each archive op.** When yesterday's README becomes a new archive, its predecessor (which previously had `[Today →]`) is updated so its "next" link points at the newly archived file. *Only that one neighbor file is rewritten* — the chain is not walked. This is the only file other than today's README and the new archive that the runtime ever modifies.
- **Tracked users = followed + custom.** `GitHubDigest.collect_tracked_users` merges `main_user.get_following()` with logins from `custom_users.txt` (deduped by login, followed first, organizations dropped). The custom file is optional; missing file → empty list. Format: one login per line, `#` comments, optional `@` prefix stripped, blanks ignored.
- **Event fetch terminates early.** `get_events_for_tracked_users` iterates each tracked user's events newest-first and `break`s as soon as it sees an event older than today. Don't reorder or filter the iterator before this loop.
- **Organizations are skipped on both paths** (followed *and* custom). The events API returns 404 for org logins.
- **Only four event types render** (`EventLineBuilder.format_event`): `WatchEvent`, `ForkEvent`, `CreateEvent` with `ref_type == "repository"`, `PublicEvent`. Anything else returns `None` and drops.
- **Repo-description fetch can hit deleted/private repos.** `event.repo.description` is wrapped in `try/except github.UnknownObjectException`; keep that wrapper or one missing repo will fail the run.
- **Per-user event dedup is exact-string** on the rendered line. Changing line format changes dedup behavior.

## CI / commit flow

The workflow auto-commits `README.md`, `archive/`, and `custom_users.txt` with message `docs(activity): refresh activity @ <UTC timestamp>`, then rebases on `origin/main` (falling back to merge) and retries `git push` up to 3 times. Hand-written commits to `main` will race with the hourly job — expect rebases. Don't push commits that depend on README content; it gets overwritten every hour.
