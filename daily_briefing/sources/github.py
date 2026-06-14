"""GitHub source — fetches activity via `gh` CLI.

Strategy: use `gh` CLI subcommands (GraphQL-backed) which work with minimal
token scopes. The REST API `/notifications` requires the `notifications` scope
which this token may not have — we fall back to `gh issue list` and `gh pr list`
which work with just `repo` scope.

Relevant `gh` CLI docs:
  - `gh issue list`: https://cli.github.com/manual/gh_issue_list
  - `gh pr list`: https://cli.github.com/manual/gh_pr_list
  - `gh repo list`: https://cli.github.com/manual/gh_repo_list
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from daily_briefing.sources.base import SourceProtocol, SourceResult

MAX_ISSUES = 5
MAX_PRS = 3
MAX_RECENT_REPOS = 5


class GitHubSource(SourceProtocol):
    """Fetches GitHub activity via the `gh` CLI."""

    name = "github"

    def fetch(self, config: dict[str, Any]) -> SourceResult:
        """Fetch issues, PRs, and recent repo activity from GitHub."""
        if not self._has_gh():
            return SourceResult(
                name=self.name,
                priority=30,
                error="`gh` CLI not found or not authenticated. Run: gh auth login",
            )

        issues = []
        prs = []
        recent_repos = []
        errors = []

        try:
            issues = self._get_issues()
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            errors.append(f"Issues: {e}")

        try:
            prs = self._get_prs()
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            errors.append(f"PRs: {e}")

        try:
            recent_repos = self._get_recent_repos()
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            errors.append(f"Repos: {e}")

        # Only report error if ALL sub-queries failed
        if not issues and not prs and not recent_repos and errors:
            return SourceResult(
                name=self.name,
                priority=30,
                error="; ".join(errors),
            )

        return SourceResult(
            name=self.name,
            priority=30,
            data={
                "open_issues": issues,
                "open_prs": prs,
                "recent_repos": recent_repos,
                "total_issues": len(issues),
                "total_prs": len(prs),
            },
        )

    def _has_gh(self) -> bool:
        """Check if `gh` CLI is available and authenticated."""
        try:
            subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_issues(self) -> list[dict[str, Any]]:
        """Fetch open issues assigned to the user."""
        # Fields available: assignees, author, body, closed, closedAt, comments,
        # createdAt, id, labels, milestone, number, projectCards, projectItems,
        # reactionGroups, state, title, updatedAt, url
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--assignee", "@me",
                "--state", "open",
                "--limit", str(MAX_ISSUES),
                "--json", "title,url,updatedAt",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)

    def _get_prs(self) -> list[dict[str, Any]]:
        """Fetch open PRs the user is involved in (author or requested review)."""
        # Check PRs where user is requested reviewer first (most actionable),
        # then authored PRs.
        review_prs = []
        authored_prs = []

        try:
            r = subprocess.run(
                [
                    "gh", "pr", "list",
                    "--search", "review-requested:@me",
                    "--state", "open",
                    "--limit", str(MAX_PRS),
                    "--json", "title,url,createdAt,headRepository",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            if r.stdout.strip():
                for pr in json.loads(r.stdout):
                    pr["_kind"] = "review_requested"
                    review_prs.append(pr)
        except subprocess.CalledProcessError:
            pass  # Search might not be supported; skip gracefully

        try:
            r = subprocess.run(
                [
                    "gh", "pr", "list",
                    "--author", "@me",
                    "--state", "open",
                    "--limit", str(MAX_PRS),
                    "--json", "title,url,createdAt,headRepository",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=True,
            )
            if r.stdout.strip():
                for pr in json.loads(r.stdout):
                    pr["_kind"] = "authored"
                    authored_prs.append(pr)
        except subprocess.CalledProcessError:
            pass

        # Merge: review-requested first (more actionable), then authored
        return (review_prs + authored_prs)[:MAX_PRS]

    def _get_recent_repos(self) -> list[dict[str, Any]]:
        """Fetch recently pushed repos (to show what you've been working on)."""
        result = subprocess.run(
            [
                "gh", "repo", "list",
                "--limit", str(MAX_RECENT_REPOS),
                "--json", "name,updatedAt,pushedAt",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)
