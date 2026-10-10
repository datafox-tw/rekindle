"""Collects the three signal layers for a failed, timed-out or slow run."""


def collect_k8s(namespace: str, app_name: str) -> dict:
    """Pod statuses, container termination reasons and exit codes, namespace events."""
    raise NotImplementedError


def collect_logs(namespace: str, app_name: str) -> dict:
    """Driver and executor log excerpts around errors, plus exception stack traces."""
    raise NotImplementedError


def collect_event_log(uri: str) -> dict:
    """Fetch the run's Spark event log and summarise it with services.eventlog."""
    raise NotImplementedError
