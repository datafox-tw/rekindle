"""Tools for the investigate node. All read-only: logs are untrusted input, so nothing
the model reads can be allowed to trigger a write."""


def get_k8s_events(incident_id: str) -> list[dict]:
    """Pod statuses, container exit reasons and namespace events for the incident's run."""
    raise NotImplementedError


def get_log_excerpt(incident_id: str, pod: str, around: str) -> str:
    """Lines around a pattern in a driver or executor log."""
    raise NotImplementedError


def get_eventlog_summary(incident_id: str) -> dict:
    """Per-stage durations, task skew, spill and executor removal reasons."""
    raise NotImplementedError


def get_spark_conf(incident_id: str) -> dict[str, str]:
    """The Spark conf the failed run was submitted with."""
    raise NotImplementedError
