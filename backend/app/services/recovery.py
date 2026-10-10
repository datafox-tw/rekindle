"""Applies fixes: whitelist check, resubmit, verification."""

from pathlib import Path

WHITELIST_PATH = Path(__file__).resolve().parents[1] / "fix_whitelist.yaml"


def validate_fix(conf: dict[str, str]) -> list[str]:
    """Return the violations; empty means every key is whitelisted and within bounds."""
    raise NotImplementedError


def resubmit(run_id: str, conf: dict[str, str]) -> str:
    """Create a new SparkApplication from the original with `conf` applied. Returns its run id."""
    raise NotImplementedError


def verify(run_id: str) -> bool:
    """The rerun succeeded and its duration is within the baseline range."""
    raise NotImplementedError
