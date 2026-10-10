from fastapi import FastAPI, HTTPException

app = FastAPI(title="Rekindle")


def _not_implemented() -> None:
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/lab/runs")
def start_lab_run() -> None:
    """Start a live fault run (quota-limited) or request a replay of a recorded one."""
    _not_implemented()


@app.post("/api/uploads")
def upload_event_log() -> None:
    """Accept an event log, redact it, and produce a diagnosis report. Never executes anything."""
    _not_implemented()


@app.get("/api/metrics")
def metrics() -> None:
    """Latest evaluation numbers for the public metrics page."""
    _not_implemented()
