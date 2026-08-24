"""Small GitHub API client used by the CLI."""

from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any, Callable


_RUN_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/actions/runs/"
    r"(?P<run_id>\d+)(?:[/?#].*)?$"
)


class GitHubAPIError(RuntimeError):
    """Raised when GitHub data cannot be fetched or decoded."""


@dataclass(frozen=True, slots=True)
class RunReference:
    """Parsed owner/repository/run identity from an Actions run URL."""

    owner: str
    repository: str
    run_id: int


def parse_run_url(url: str) -> RunReference:
    """Parse a canonical GitHub Actions run URL."""
    match = _RUN_RE.match(url.strip())
    if not match:
        raise ValueError(
            "Expected a GitHub Actions run URL like "
            "https://github.com/OWNER/REPO/actions/runs/123456"
        )
    return RunReference(
        owner=match.group("owner"),
        repository=match.group("repo"),
        run_id=int(match.group("run_id")),
    )


class GitHubAPIClient:
    """Read-only GitHub Actions client using the public REST API."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout: int = 20,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._token = token
        self._timeout = timeout
        self._opener = opener

    def _request(self, url: str, *, accept: str = "application/vnd.github+json") -> bytes:
        headers = {
            "Accept": accept,
            "User-Agent": "gha-log-parser/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self._opener(request, timeout=self._timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise GitHubAPIError(f"GitHub API HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise GitHubAPIError(f"GitHub API network error: {exc.reason}") from exc

    def get_jobs(self, ref: RunReference) -> list[dict[str, Any]]:
        """Return jobs for a workflow run."""
        url = (
            f"https://api.github.com/repos/{ref.owner}/{ref.repository}/actions/"
            f"runs/{ref.run_id}/jobs?per_page=100"
        )
        try:
            payload = json.loads(self._request(url).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GitHubAPIError("GitHub jobs response was not valid JSON") from exc
        jobs = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(jobs, list):
            raise GitHubAPIError("GitHub jobs response did not contain a jobs list")
        return [row for row in jobs if isinstance(row, dict)]

    def get_job_log_text(self, owner: str, repository: str, job_id: int) -> str:
        """Download and normalize the log for one Actions job."""
        url = f"https://api.github.com/repos/{owner}/{repository}/actions/jobs/{job_id}/logs"
        raw = self._request(url, accept="application/vnd.github+json")
        if raw[:2] == b"PK":
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    chunks = []
                    for name in sorted(archive.namelist()):
                        if name.endswith("/"):
                            continue
                        chunks.append(archive.read(name).decode("utf-8", errors="replace"))
                    return "\n".join(chunks)
            except zipfile.BadZipFile as exc:
                raise GitHubAPIError("GitHub returned an unreadable log archive") from exc
        return raw.decode("utf-8", errors="replace")
