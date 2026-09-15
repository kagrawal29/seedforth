from pathlib import Path


PROTOCOL = Path(__file__).parents[1] / "mycelium" / "graph" / "protocols" / "system-constraint-observer.cypher"


def test_system_constraint_observer_is_shadow_only_and_idempotent():
    text = PROTOCOL.read_text(encoding="utf-8")

    assert "MERGE (g:GapSignal" in text
    assert "intervention_enabled = false" in text
    assert "mode = 'shadow'" in text
    assert "SET a.status" not in text
    assert "SET w.status" not in text
    assert "DETACH DELETE" not in text
