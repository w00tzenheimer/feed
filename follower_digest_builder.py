from __future__ import annotations

import argparse
import logging
import os
import re
import datetime
import pathlib
import string
import typing

import github  # type: ignore

# Read-only, compiled regex pattern(s)
FIRST_LINE_DATE_PATTERN = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")

# Read-only module-level template for README content
README_TEMPLATE = string.Template("""# Daily GitHub Activity (${today_str})

Today's public activity from users I follow (updated every 15 minutes).

## Today's Activity

${todays_events_md}
---
*Last updated at ${last_updated} UTC*
*Historical records are stored in the `archive` directory.*
""")

# Read-only module-level template for user section content
USER_SECTION_TEMPLATE = string.Template("""### [${username}](https://github.com/${username})
${activities}

""")


class EventLineBuilder:
    """
    A composable, unit-testable class for building markdown lines from GitHub events.
    """
    def __init__(
        self,
        logger: logging.Logger,
        max_desc_len: int = 100
    ):
        self.logger: logging.Logger = logger
        self.max_desc_len: int = max_desc_len

    def append_description(self, line: str, description: typing.Optional[str]) -> str:
        """
        Append a formatted description to a line if both line and description exist.
        """
        if line and description:
            if len(description) > self.max_desc_len:
                description = description[:self.max_desc_len] + "..."
            # Format the description as a Markdown blockquote with line breaks and indentation
            desc_line = description.replace('\n', ' ').replace('\r', ' ')
            line += "\n  > %s" % desc_line
        return line

    def format_event(self, event: typing.Any) -> typing.Optional[str]:
        """
        Format a GitHub event into a friendly Markdown list item,
        including the repository description.
        """
        try:
            actor_login = event.actor.login
            actor_url = event.actor.html_url
            repo_name = event.repo.name
            repo_url = f"https://github.com/{repo_name}"

            # Try to get the repository description; handle gracefully if the repo does not exist or is inaccessible
            try:
                description = event.repo.description
            except github.UnknownObjectException:
                self.logger.warning("Repository %s is inaccessible (may be deleted or private), skipping description.", repo_name)
                description = None

            # We only care about certain meaningful event types
            match event.type:
                case "WatchEvent":
                    line = "- 🌟 👤 [{0}]({1}) Starred [{2}]({3})".format(actor_login, actor_url, repo_name, repo_url)
                case "ForkEvent":
                    forked_to = event.payload["forkee"]["full_name"]
                    line = "- 🍴 👤 [{0}]({1}) Forked [{2}]({3}) to [{4}](https://github.com/{4})".format(
                        actor_login, actor_url, repo_name, repo_url, forked_to
                    )
                case "CreateEvent" if event.payload.get("ref_type") == "repository":
                    line = "- ✨ 👤 [{0}]({1}) Created new repo [{2}]({3})".format(actor_login, actor_url, repo_name, repo_url)
                case "PublicEvent":
                    line = "- 🚀 👤 [{0}]({1}) Made [{2}]({3}) public".format(actor_login, actor_url, repo_name, repo_url)
                case _:
                    line = ""

            line = self.append_description(line, description)

            return line or None

        except Exception as e:
            self.logger.exception("An unknown error occurred while formatting the event: %s", e)
            return None


class GitHubDigest:
    def __init__(
        self,
        github_token: str,
        github_username: str,
        archive_dir: str = "archive",
        readme_file: str = "README.md"
    ):
        self.github_token: str = github_token
        self.github_username: str = github_username
        self.archive_dir: str = archive_dir
        self.readme_file: str = readme_file
        self.github: typing.Optional[github.Github] = None
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.line_builder: EventLineBuilder = EventLineBuilder(self.logger)

    def setup_github(self) -> None:
        self.logger.debug("Authenticating to GitHub...")
        auth = github.Auth.Token(self.github_token)
        self.github = github.Github(auth=auth)


    def archive_if_yesterday(self, yesterday_str: str) -> None:
        """
        Archive the README if it contains yesterday's content.
        """
        readme_path = pathlib.Path(self.readme_file)
        if not readme_path.exists():
            self.logger.info("%s does not exist; skipping archive step.", self.readme_file)
            return

        content = readme_path.read_text(encoding="utf-8")
        if not content.strip():
            self.logger.info("%s is empty; skipping archive step.", self.readme_file)
            return

        first_line = content.splitlines()[0]
        match = FIRST_LINE_DATE_PATTERN.search(first_line)

        if match and match.group(1) == yesterday_str:
            archive_path = pathlib.Path(self.archive_dir) / f"{yesterday_str}.md"
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_path.write_text(content, encoding="utf-8")
            self.logger.info("Successfully archived the report for %s to %s", yesterday_str, archive_path)
        else:
            self.logger.info("README does not need to be archived.")

    def get_events_from_followed_users(
        self,
        today_date_utc: datetime.date,
    ) -> typing.List[typing.Any]:
        """
        Get today's public activity from all users followed by the specified user.
        """
        if self.github is None:
            raise RuntimeError("GitHub client is not initialized. Call setup_github() first.")

        try:
            main_user = self.github.get_user(self.github_username)
        except Exception as e:
            self.logger.error("Could not fetch user '%s': %s", self.github_username, e)
            raise

        following = main_user.get_following()
        todays_events: typing.List[typing.Any] = []
        self.logger.info("Fetching today's activity for all users followed by %s...", self.github_username)

        for followed_user in following:
            # Skip organizations as they don't support the events API endpoint
            if followed_user.type == "Organization":
                self.logger.debug("  -> Skipping organization %s (organizations not supported)", followed_user.login)
                continue

            self.logger.info("  -> Fetching activity for %s...", followed_user.login)
            try:
                events = followed_user.get_events()
                for event in events:
                    event_date = event.created_at.date()
                    if event_date < today_date_utc:
                        break  # No more events for today for this user
                    if event_date == today_date_utc:
                        todays_events.append(event)
            except Exception as e:
                self.logger.warning("  -> Error fetching activity for user %s: %s", followed_user.login, e)

        # Sort all events in reverse chronological order to ensure newest events come first
        todays_events.sort(key=lambda e: e.created_at, reverse=True)
        self.logger.debug("Collected %d events for today.", len(todays_events))
        return todays_events

    def generate_markdown_for_events(self, events: typing.List[typing.Any]) -> str:
        """
        Generate Markdown content from a list of events.
        """
        if not events:
            return "The users you follow have no new public activity today.\n"

        events_by_user: typing.Dict[str, typing.List[str]] = {}
        for event in events:
            line = self.line_builder.format_event(event)
            if line:
                actor_login = event.actor.login
                if actor_login not in events_by_user:
                    events_by_user[actor_login] = []
                if line not in events_by_user[actor_login]:
                    events_by_user[actor_login].append(line)

        if not events_by_user:
            return (
                "The users you follow have no public activity today that matches the filter criteria.\n"
            )

        sections = []
        for username, activities in sorted(events_by_user.items()):
            section = USER_SECTION_TEMPLATE.substitute(
                username=username,
                activities="\n".join(reversed(activities))
            )
            sections.append(section)

        return "".join(sections)

    def run(self) -> None:
        if not all([self.github_token, self.github_username]):
            self.logger.error("Environment variables GITHUB_TOKEN and GITHUB_REPOSITORY_OWNER are not set")
            raise ValueError("Environment variables GITHUB_TOKEN and GITHUB_REPOSITORY_OWNER are not set")

        self.setup_github()

        today_utc = datetime.datetime.now(datetime.timezone.utc)
        yesterday_utc = today_utc - datetime.timedelta(days=1)

        today_str = today_utc.strftime("%Y-%m-%d")
        yesterday_str = yesterday_utc.strftime("%Y-%m-%d")

        self.archive_if_yesterday(yesterday_str)

        todays_events = self.get_events_from_followed_users(today_utc.date())
        self.logger.info("Found %d relevant events for today.", len(todays_events))

        todays_events_md = self.generate_markdown_for_events(todays_events)

        readme_content = README_TEMPLATE.substitute(
            today_str=today_str,
            todays_events_md=todays_events_md,
            last_updated=today_utc.strftime("%Y-%m-%d %H:%M:%S")
        )

        with open(self.readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

        self.logger.info("Successfully refreshed %s. Found %d relevant events.", self.readme_file, len(todays_events))


def get_env_or_raise(var: str) -> str:
    value = os.getenv(var)
    if value is None:
        raise ValueError(f"Environment variable {var} is not set")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a daily GitHub activity digest for users you follow."
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub API Token (default: from GITHUB_TOKEN env)",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=os.getenv("GITHUB_REPOSITORY_OWNER"),
        help="GitHub username (default: from GITHUB_REPOSITORY_OWNER env)",
    )
    parser.add_argument(
        "--archive-dir",
        type=str,
        default="archive",
        help="Directory to store archive files",
    )
    parser.add_argument(
        "--readme-file",
        type=str,
        default="README.md",
        help="README file to update",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    if not args.token or not args.username:
        raise ValueError(
            "Missing required arguments or environment variables: GITHUB_TOKEN and GITHUB_REPOSITORY_OWNER"
        )

    digest = GitHubDigest(
        github_token=args.token,
        github_username=args.username,
        archive_dir=args.archive_dir,
        readme_file=args.readme_file,
    )

    digest.run()


if __name__ == "__main__":
    main()
