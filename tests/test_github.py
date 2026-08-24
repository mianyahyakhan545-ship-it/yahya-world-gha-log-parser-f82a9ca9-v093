"""Unit tests for URL and GitHub response handling."""

import io
import json
import unittest
import zipfile

from gha_log_parser.github import GitHubAPIClient, parse_run_url


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class GitHubTests(unittest.TestCase):
    """Exercise success paths without live network calls."""

    def test_parse_run_url(self) -> None:
        ref = parse_run_url("https://github.com/acme/tool/actions/runs/123")
        self.assertEqual((ref.owner, ref.repository, ref.run_id), ("acme", "tool", 123))

    def test_invalid_run_url(self) -> None:
        with self.assertRaises(ValueError):
            parse_run_url("https://example.com/not-github")

    def test_get_jobs_mocked(self) -> None:
        body = json.dumps({"jobs": [{"id": 9, "conclusion": "failure"}]}).encode()
        client = GitHubAPIClient(opener=lambda *_args, **_kwargs: _Response(body))
        jobs = client.get_jobs(parse_run_url("https://github.com/a/b/actions/runs/1"))
        self.assertEqual(jobs[0]["id"], 9)

    def test_zip_log_is_decoded(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("1_job.txt", "error TS2322: broken")
        client = GitHubAPIClient(opener=lambda *_args, **_kwargs: _Response(buffer.getvalue()))
        text = client.get_job_log_text("a", "b", 9)
        self.assertIn("TS2322", text)
