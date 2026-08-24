"""Unit tests for CLI orchestration."""

import unittest

from gha_log_parser.cli import run
from gha_log_parser.github import RunReference


class _FakeClient:
    def __init__(self, jobs: list[dict], log: str = "") -> None:
        self.jobs = jobs
        self.log = log

    def get_jobs(self, _ref: RunReference) -> list[dict]:
        return self.jobs

    def get_job_log_text(self, _owner: str, _repo: str, _job_id: int) -> str:
        return self.log


class CLITests(unittest.TestCase):
    """Cover success and no-failure orchestration paths."""

    def test_no_failure_path(self) -> None:
        result = run(
            "https://github.com/a/b/actions/runs/1",
            client=_FakeClient([{"id": 4, "conclusion": "success"}]),
        )
        self.assertEqual(result["status"], "no_failure")

    def test_failed_step_and_json_fields(self) -> None:
        jobs = [{
            "id": 4,
            "name": "tests",
            "conclusion": "failure",
            "steps": [{"name": "Run pytest", "conclusion": "failure"}],
        }]
        result = run(
            "https://github.com/a/b/actions/runs/1",
            client=_FakeClient(jobs, "FAILED tests/test_a.py::test_a - AssertionError: bad"),
        )
        self.assertEqual(result["failing_step"], "Run pytest")
        self.assertEqual(result["suggested_fix_category"], "tests")
        self.assertIn("error_message", result)
