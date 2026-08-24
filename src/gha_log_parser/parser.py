"""Failure classification and stack-trace extraction."""

from __future__ import annotations

import re

from .models import FailureSummary

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s+")

_TEST_PATTERNS = (
    re.compile(r"\bAssertionError\b", re.I),
    re.compile(r"^FAILED\s+\S+", re.I),
    re.compile(r"\b(?:pytest|jest)\b.*\b(?:failed|failure)\b", re.I),
    re.compile(r"\bExpected:\s+.*\bReceived:\s+", re.I),
)
_BUILD_PATTERNS = (
    re.compile(r"\berror\s+TS\d+:\s+", re.I),
    re.compile(r"\b(?:compilation|build)\s+failed\b", re.I),
    re.compile(r"\bSyntaxError:\s+", re.I),
    re.compile(r"\bModuleNotFoundError:\s+", re.I),
)
_LINT_PATTERNS = (
    re.compile(r"\b(?:eslint|pylint|flake8|ruff)\b.*\b(?:error|failed|violation)\b", re.I),
    re.compile(r"\b[A-Z]\d{3,4}:\s+", re.I),
    re.compile(r"\b\d+:\d+\s+error\s+", re.I),
)
_ERROR_LINE = re.compile(
    r"(?:AssertionError|SyntaxError|TypeError|ValueError|RuntimeError|ModuleNotFoundError|"
    r"error\s+TS\d+|\berror\b|\bfailed\b)",
    re.I,
)


def _clean_lines(log_text: str) -> list[str]:
    lines: list[str] = []
    for raw in log_text.splitlines():
        value = _ANSI_RE.sub("", raw).rstrip()
        value = _TIMESTAMP_RE.sub("", value)
        lines.append(value)
    return lines


def classify_failure(log_text: str) -> tuple[str, str]:
    """Classify the primary failure and return a suggested fix category."""
    lines = _clean_lines(log_text)
    for line in lines:
        if any(pattern.search(line) for pattern in _TEST_PATTERNS):
            return "test_failure", "tests"
    for line in lines:
        if any(pattern.search(line) for pattern in _BUILD_PATTERNS):
            if "ModuleNotFoundError" in line:
                return "build_error", "dependencies"
            return "build_error", "build"
    for line in lines:
        if any(pattern.search(line) for pattern in _LINT_PATTERNS):
            return "lint_error", "lint"
    return "unknown", "unknown"


def extract_error_message(log_text: str) -> str:
    """Extract the most useful single error line from a log."""
    lines = _clean_lines(log_text)
    candidates = [line.strip() for line in lines if line.strip() and _ERROR_LINE.search(line)]
    if not candidates:
        return "No explicit error message found in the failed job log."
    # The last explicit error is often closest to the process exit and root cause.
    return candidates[-1][:1000]


def extract_stack_trace(log_text: str, *, max_lines: int = 20) -> list[str]:
    """Extract a Python traceback or JavaScript/TypeScript stack when present."""
    lines = _clean_lines(log_text)
    for index, line in enumerate(lines):
        if "Traceback (most recent call last):" in line:
            trace: list[str] = []
            for item in lines[index : index + max_lines]:
                if trace and not item.strip():
                    break
                trace.append(item.strip())
            return trace

    for index, line in enumerate(lines):
        if re.search(r"(?:Error|AssertionError|TypeError|SyntaxError):", line):
            trace = [line.strip()]
            for item in lines[index + 1 : index + max_lines]:
                stripped = item.strip()
                if stripped.startswith("at ") or stripped.startswith("at async "):
                    trace.append(stripped)
                elif len(trace) > 1:
                    break
            if len(trace) > 1:
                return trace
    return []


def parse_failure(
    *,
    run_url: str,
    owner: str,
    repository: str,
    run_id: int,
    job_name: str,
    failing_step: str,
    log_text: str,
) -> FailureSummary:
    """Convert one failed job log into the required structured summary."""
    failure_type, suggested = classify_failure(log_text)
    return FailureSummary(
        run_url=run_url,
        owner=owner,
        repository=repository,
        run_id=run_id,
        job_name=job_name,
        failing_step=failing_step or "unknown",
        failure_type=failure_type,
        error_message=extract_error_message(log_text),
        stack_trace=extract_stack_trace(log_text),
        suggested_fix_category=suggested,
    )
