"""GitHub Actions log parser package."""

from .models import FailureSummary
from .parser import parse_failure

__all__ = ["FailureSummary", "parse_failure"]
