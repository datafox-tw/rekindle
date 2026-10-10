import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Run(Base):
    """One SparkApplication execution. A resubmit points at the run it retries."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source: Mapped[str]  # lab | eval
    fault_id: Mapped[str | None]
    spark_conf: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str]
    duration_s: Mapped[float | None]
    est_cost_usd: Mapped[float | None]
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Incident(Base):
    """One triage case. Uploaded event logs have no run."""

    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id"))
    signature: Mapped[str | None] = mapped_column(index=True)
    root_cause: Mapped[str | None]
    matched_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"))
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Evidence(Base):
    """Summary of one signal layer for an incident, plus where the raw file lives."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    layer: Mapped[str]  # k8s | log | event_log
    summary: Mapped[dict] = mapped_column(JSONB)
    raw_uri: Mapped[str | None]


class Case(Base):
    """Case base entry: a fingerprint and the fix that was verified for it."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    signature: Mapped[str] = mapped_column(unique=True)
    embedding = mapped_column(Vector(get_settings().embedding_dim))
    root_cause: Mapped[str]
    fix: Mapped[dict] = mapped_column(JSONB)
    verified: Mapped[bool] = mapped_column(default=False)
    demoted: Mapped[bool] = mapped_column(default=False)
    hit_count: Mapped[int] = mapped_column(default=0)
    success_count: Mapped[int] = mapped_column(default=0)
    failure_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AgentStep(Base):
    """One graph node execution. Feeds the timeline and the cost numbers."""

    __tablename__ = "agent_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    node: Mapped[str]
    summary: Mapped[dict] = mapped_column(JSONB)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    duration_s: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Report(Base):
    """Diagnosis report for an uploaded event log. Deleted after it expires."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    body: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime]


class EvalResult(Base):
    """One incident's outcome within an evaluation run."""

    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    eval_run: Mapped[str] = mapped_column(index=True)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id"))
    expected_root_cause: Mapped[str]
    correct: Mapped[bool]
