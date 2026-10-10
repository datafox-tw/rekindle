"""Triage loop. The wiring and routing are real; the node bodies are stubs.

LLM calls belong only in investigate, classify and propose_fix. Every other node is
deterministic, so a case-base hit never spends investigation tokens.
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.schemas import Diagnosis, ProposedFix, RootCause
from app.config import get_settings


class TriageState(TypedDict, total=False):
    incident_id: str
    signature: str
    case_id: str | None  # matched case, set by lookup
    diagnosis: Diagnosis | None  # stays None on the hit path until an investigation runs
    proposed_fix: ProposedFix | None
    fix_valid: bool
    proposal_attempts: int
    resubmit_attempts: int
    verified: bool


def collect(state: TriageState) -> TriageState:
    """Gather K8s events, driver/executor log excerpts and the event log summary."""
    raise NotImplementedError


def fingerprint(state: TriageState) -> TriageState:
    """Normalise the key error into a signature hash and an embedding."""
    raise NotImplementedError


def lookup(state: TriageState) -> TriageState:
    """Search the case base. On a hit, set case_id and proposed_fix from the case."""
    raise NotImplementedError


def investigate(state: TriageState) -> TriageState:
    """Tool-using investigation with a step cap. Tools are read-only."""
    raise NotImplementedError


def classify(state: TriageState) -> TriageState:
    """Structured output: one RootCause, a confidence and the supporting evidence."""
    raise NotImplementedError


def propose_fix(state: TriageState) -> TriageState:
    """Structured output: a Spark conf diff. Increments proposal_attempts."""
    raise NotImplementedError


def validate_fix(state: TriageState) -> TriageState:
    """Check proposed_fix against the whitelist and its bounds. Sets fix_valid."""
    raise NotImplementedError


def resubmit(state: TriageState) -> TriageState:
    """Create a new SparkApplication with the fix applied. Increments resubmit_attempts."""
    raise NotImplementedError


def verify(state: TriageState) -> TriageState:
    """Rerun succeeded and its duration is within the baseline range. Sets verified.

    When a case-base hit fails here, demote the matched case before returning.
    """
    raise NotImplementedError


def write_back(state: TriageState) -> TriageState:
    """Record the outcome: add or credit a case, or mark the incident as needing a human."""
    raise NotImplementedError


def route_after_lookup(state: TriageState) -> Literal["hit", "miss"]:
    return "hit" if state.get("case_id") else "miss"


def route_after_classify(state: TriageState) -> Literal["fixable", "needs_human"]:
    return "needs_human" if state["diagnosis"].category is RootCause.NEEDS_HUMAN else "fixable"


def route_after_validate(
    state: TriageState,
) -> Literal["resubmit", "investigate", "propose_fix", "write_back"]:
    if state["fix_valid"]:
        return "resubmit"
    if state.get("diagnosis") is None:
        # A stored fix that no longer passes the whitelist: treat the hit as a miss.
        return "investigate"
    if state.get("proposal_attempts", 0) < get_settings().max_fix_proposals:
        return "propose_fix"
    return "write_back"


def route_after_verify(state: TriageState) -> Literal["write_back", "investigate"]:
    if state["verified"] or state.get("resubmit_attempts", 0) >= get_settings().max_resubmits:
        return "write_back"
    return "investigate"


def build_graph(checkpointer=None):
    g = StateGraph(TriageState)
    for node in (
        collect,
        fingerprint,
        lookup,
        investigate,
        classify,
        propose_fix,
        validate_fix,
        resubmit,
        verify,
        write_back,
    ):
        g.add_node(node.__name__, node)

    g.add_edge(START, "collect")
    g.add_edge("collect", "fingerprint")
    g.add_edge("fingerprint", "lookup")
    g.add_conditional_edges(
        "lookup", route_after_lookup, {"hit": "validate_fix", "miss": "investigate"}
    )
    g.add_edge("investigate", "classify")
    g.add_conditional_edges(
        "classify", route_after_classify, {"fixable": "propose_fix", "needs_human": "write_back"}
    )
    g.add_edge("propose_fix", "validate_fix")
    g.add_conditional_edges(
        "validate_fix",
        route_after_validate,
        ["resubmit", "investigate", "propose_fix", "write_back"],
    )
    g.add_edge("resubmit", "verify")
    g.add_conditional_edges("verify", route_after_verify, ["write_back", "investigate"])
    g.add_edge("write_back", END)
    return g.compile(checkpointer=checkpointer)
