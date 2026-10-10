from app.models import Base


def test_tables_match_design_doc():
    assert set(Base.metadata.tables) == {
        "runs",
        "incidents",
        "evidence",
        "cases",
        "agent_steps",
        "reports",
        "eval_results",
    }
