"""Streaming parser for Spark event logs. Shared by the fault lab and the upload path."""

from collections.abc import Iterable


def summarize(lines: Iterable[str]) -> dict:
    """Per-stage durations, task duration and shuffle-read skew, spill, executor removals.

    Must tolerate a truncated file: a killed driver leaves the log as `.inprogress`.
    """
    raise NotImplementedError
