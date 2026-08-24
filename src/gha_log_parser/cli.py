"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .github import GitHubAPIClient, GitHubAPIError, parse_run_url
from .parser import parse_failure


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="gha-log-parser",
        description="Extract structured failure information from a GitHub Actions run.",
    )
    parser.add_argument("run_url", help="GitHub Actions run URL")
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub token; defaults to GITHUB_TOKEN. Public runs may work without one.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def _failed_step(job: dict[str, Any]) -> str:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return "unknown"
    for step in steps:
        if isinstance(step, dict) and str(step.get("conclusion") or "").lower() == "failure":
            return str(step.get("name") or "unknown")
    return "unknown"


def run(
    run_url: str,
    *,
    token: str | None = None,
    client: GitHubAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch a workflow run and return the first failed job as structured JSON data."""
    ref = parse_run_url(run_url)
    api = client or GitHubAPIClient(token=token)
    jobs = api.get_jobs(ref)
    failed = [job for job in jobs if str(job.get("conclusion") or "").lower() == "failure"]
    if not failed:
        return {
            "run_url": run_url,
            "owner": ref.owner,
            "repository": ref.repository,
            "run_id": ref.run_id,
            "status": "no_failure",
            "failing_step": None,
            "error_message": None,
            "stack_trace": [],
            "suggested_fix_category": None,
        }

    job = failed[0]
    job_id = job.get("id")
    if not isinstance(job_id, int):
        raise GitHubAPIError("Failed job did not contain an integer job id")
    log_text = api.get_job_log_text(ref.owner, ref.repository, job_id)
    summary = parse_failure(
        run_url=run_url,
        owner=ref.owner,
        repository=ref.repository,
        run_id=ref.run_id,
        job_name=str(job.get("name") or "unknown"),
        failing_step=_failed_step(job),
        log_text=log_text,
    )
    data = summary.as_dict()
    data["status"] = "failure"
    return data


def main() -> int:
    """Run the CLI and return a process exit code."""
    args = build_parser().parse_args()
    try:
        result = run(args.run_url, token=args.token)
    except (ValueError, GitHubAPIError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
