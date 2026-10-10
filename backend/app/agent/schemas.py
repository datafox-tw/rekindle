from enum import StrEnum

from pydantic import BaseModel, Field


class RootCause(StrEnum):
    """Fixed triage taxonomy. Candidates until the fault lab is finalised in phase 1."""

    EXECUTOR_CONTAINER_OOM = "executor_container_oom"
    EXECUTOR_HEAP_OOM = "executor_heap_oom"
    DATA_SKEW = "data_skew"
    NODE_PREEMPTION = "node_preemption"
    DRIVER_OOM = "driver_oom"
    UNSCHEDULABLE = "unschedulable"
    # Not fixable by whitelisted config; the loop stops and reports instead of forcing a fix.
    NEEDS_HUMAN = "needs_human"


class SignalLayer(StrEnum):
    K8S = "k8s"
    LOG = "log"
    EVENT_LOG = "event_log"


class EvidenceRef(BaseModel):
    layer: SignalLayer
    excerpt: str


class Diagnosis(BaseModel):
    category: RootCause
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceRef]


class ProposedFix(BaseModel):
    conf: dict[str, str]  # Spark conf key -> new value
    rationale: str
