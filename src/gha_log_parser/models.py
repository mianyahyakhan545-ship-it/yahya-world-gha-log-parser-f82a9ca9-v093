"""Typed models for parsed GitHub Actions failures."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FailureSummary:
    """Structured summary of one failed GitHub Actions run."""

    run_url: str
    owner: str
    repository: str
    run_id: int
    job_name: str
    failing_step: str
    failure_type: str
    error_message: str
    stack_trace: list[str]
    suggested_fix_category: str

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)
