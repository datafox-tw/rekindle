from app.agent.graph import (
    build_graph,
    route_after_classify,
    route_after_lookup,
    route_after_validate,
    route_after_verify,
)
from app.agent.schemas import Diagnosis, RootCause
from app.config import get_settings


def diagnosis(category: RootCause) -> Diagnosis:
    return Diagnosis(category=category, confidence=0.9, evidence=[])


def test_graph_compiles_with_all_nodes():
    nodes = set(build_graph().get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {
        "collect",
        "fingerprint",
        "lookup",
        "investigate",
        "classify",
        "propose_fix",
        "validate_fix",
        "resubmit",
        "verify",
        "write_back",
    }


def test_hit_skips_investigation():
    assert route_after_lookup({"case_id": "c1"}) == "hit"
    assert route_after_lookup({"case_id": None}) == "miss"


def test_needs_human_skips_fix():
    assert route_after_classify({"diagnosis": diagnosis(RootCause.NEEDS_HUMAN)}) == "needs_human"
    assert route_after_classify({"diagnosis": diagnosis(RootCause.DATA_SKEW)}) == "fixable"


def test_invalid_fix_retries_then_gives_up():
    cap = get_settings().max_fix_proposals
    investigated = {"fix_valid": False, "diagnosis": diagnosis(RootCause.DATA_SKEW)}
    assert route_after_validate({"fix_valid": True}) == "resubmit"
    assert route_after_validate({**investigated, "proposal_attempts": cap - 1}) == "propose_fix"
    assert route_after_validate({**investigated, "proposal_attempts": cap}) == "write_back"


def test_invalid_stored_fix_falls_back_to_investigation():
    assert route_after_validate({"fix_valid": False, "case_id": "c1"}) == "investigate"


def test_failed_verification_reinvestigates_until_resubmit_cap():
    cap = get_settings().max_resubmits
    assert route_after_verify({"verified": True, "resubmit_attempts": 1}) == "write_back"
    assert route_after_verify({"verified": False, "resubmit_attempts": cap - 1}) == "investigate"
    assert route_after_verify({"verified": False, "resubmit_attempts": cap}) == "write_back"
