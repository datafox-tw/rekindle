"""Case base: lookup, write-back and demotion."""

import uuid


def find(signature: str, embedding: list[float]) -> uuid.UUID | None:
    """Exact signature match first, then nearest verified case above the similarity threshold.

    Demoted cases never match here.
    """
    raise NotImplementedError


def record_outcome(case_id: uuid.UUID, success: bool) -> None:
    """Credit a hit that verified, or demote the case when its fix failed."""
    raise NotImplementedError


def add(signature: str, embedding: list[float], root_cause: str, fix: dict) -> uuid.UUID:
    """Store a newly verified case."""
    raise NotImplementedError
