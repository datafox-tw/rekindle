"""Turns an incident's key error into something the case base can match on."""


def normalize(error_text: str) -> str:
    """Replace app IDs, pod names, executor numbers, IPs, timestamps, paths and numbers."""
    raise NotImplementedError


def signature(normalized: str) -> str:
    """SHA-256 of the normalised error, used for exact matching."""
    raise NotImplementedError


def embed(normalized: str, features: dict) -> list[float]:
    """Embedding of the normalised error plus structured features, for near matching."""
    raise NotImplementedError
