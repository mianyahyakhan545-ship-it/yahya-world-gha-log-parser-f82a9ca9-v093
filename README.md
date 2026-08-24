# GitHub Actions Log Parser CLI

`gha-log-parser` accepts a GitHub Actions run URL, downloads the failed job logs through the GitHub REST API, identifies the failing step, and emits a structured JSON summary for CI triage systems.

## Features

- Accepts URLs such as `https://github.com/OWNER/REPO/actions/runs/123456789`.
- Emits JSON with the failing step, error message, stack trace, failure type, and suggested fix category.
- Recognizes pytest/Jest test failures, TypeScript/compilation failures, and common lint failures.
- Supports GitHub job-log ZIP responses as well as plain-text logs.
- Uses only the Python standard library at runtime.
- Optional `GITHUB_TOKEN` support for private repositories or higher API limits.

## Installation

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Usage

```bash
gha-log-parser https://github.com/acme/widget/actions/runs/123456789 --pretty
```

For private repositories:

```bash
export GITHUB_TOKEN=github_pat_xxx
gha-log-parser https://github.com/acme/private-repo/actions/runs/123456789 --pretty
```

## Example output

```json
{
  "error_message": "FAILED tests/test_math.py::test_add - AssertionError: assert 3 == 4",
  "failing_step": "Run pytest",
  "failure_type": "test_failure",
  "job_name": "tests",
  "owner": "acme",
  "repository": "widget",
  "run_id": 123456789,
  "run_url": "https://github.com/acme/widget/actions/runs/123456789",
  "stack_trace": [],
  "status": "failure",
  "suggested_fix_category": "tests"
}
```

## Failure categories

| Failure | Detection examples | Suggested fix category |
| --- | --- | --- |
| Tests | pytest `FAILED`, `AssertionError`, Jest failures | `tests` |
| Build | `error TS2322`, compilation failures, syntax errors | `build` |
| Dependency | `ModuleNotFoundError` | `dependencies` |
| Lint | ESLint/Pylint/Flake8/Ruff-style errors | `lint` |
| Unknown | no recognized signature | `unknown` |

## Testing

The test suite uses mocked GitHub API responses; it does not require network access.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers URL parsing, mocked job discovery, ZIP log decoding, successful runs, pytest/Jest failures, TypeScript build errors, lint errors, stack traces, and required JSON fields.

## Notes

GitHub's job logs endpoint may redirect to a temporary archive URL. `urllib` follows the redirect automatically. The parser strips common GitHub timestamps and ANSI color sequences before classifying failures.
