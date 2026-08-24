"""Unit tests for log parsing."""

import unittest

from gha_log_parser.parser import classify_failure, extract_stack_trace, parse_failure


class ParserTests(unittest.TestCase):
    """Cover the required failure categories."""

    def test_pytest_failure(self) -> None:
        log = (
            "Run pytest\n"
            "FAILED tests/test_math.py::test_add - AssertionError: assert 3 == 4\n"
        )
        failure_type, fix = classify_failure(log)
        self.assertEqual((failure_type, fix), ("test_failure", "tests"))

    def test_jest_failure(self) -> None:
        log = (
            "Jest test suite failed\n"
            "Expected: 2 Received: 3\n"
            "Error: expect(received).toBe(expected)\n"
            "    at Object.<anonymous> (a.test.js:3:1)\n"
        )
        failure_type, fix = classify_failure(log)
        self.assertEqual((failure_type, fix), ("test_failure", "tests"))

    def test_typescript_build_failure(self) -> None:
        log = "src/app.ts(3,4): error TS2322: Type 'string' is not assignable to type 'number'."
        failure_type, fix = classify_failure(log)
        self.assertEqual((failure_type, fix), ("build_error", "build"))

    def test_lint_failure(self) -> None:
        log = "src/app.ts\n  10:2  error  Unexpected any  @typescript-eslint/no-explicit-any"
        failure_type, fix = classify_failure(log)
        self.assertEqual((failure_type, fix), ("lint_error", "lint"))

    def test_python_traceback_is_extracted(self) -> None:
        log = (
            "Traceback (most recent call last):\n"
            "  File \"main.py\", line 2, in <module>\n"
            "    raise ValueError('bad')\n"
            "ValueError: bad\n\n"
            "Process completed with exit code 1.\n"
        )
        trace = extract_stack_trace(log)
        self.assertGreaterEqual(len(trace), 4)
        self.assertIn("ValueError: bad", trace[-1])

    def test_summary_contains_required_fields(self) -> None:
        summary = parse_failure(
            run_url="https://github.com/o/r/actions/runs/7",
            owner="o",
            repository="r",
            run_id=7,
            job_name="tests",
            failing_step="pytest",
            log_text="FAILED tests/test_x.py::test_x - AssertionError: no",
        ).as_dict()
        for field in ("failing_step", "error_message", "stack_trace", "suggested_fix_category"):
            self.assertIn(field, summary)
