"""Redacts uploaded event logs. Runs before anything is stored or sent to an LLM."""

from collections.abc import Iterable, Iterator


def redact(lines: Iterable[str]) -> Iterator[str]:
    """Keep only allow-listed conf keys; mask SQL literals, file paths and host names."""
    raise NotImplementedError
