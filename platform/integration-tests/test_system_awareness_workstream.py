from pathlib import Path


WORKSTREAM = (
    Path(__file__).parents[1]
    / "mycelium"
    / "graph"
    / "knowledge"
    / "system-awareness-metabolism-workstream.cypher"
)


def test_awareness_workstream_is_bounded_and_non_preemptive():
    text = WORKSTREAM.read_text(encoding="utf-8")

    assert "workstream-system-awareness-metabolism" in text
    assert "goal-system-awareness-metabolism" in text
    assert "knowledge-system-awareness-metabolism-workstream" in text
    assert "goal-seedforth-upgrade-20260906" in text
    assert text.count("id:'W0") >= 8
    assert "w.status='proposed'" in text
    assert "w.execution_eligible=false" in text
    assert "requires_explicit_priority_admission" in text
    assert "MERGE (w)-[:DEPENDS_ON]->(d)" in text


def test_awareness_workstream_does_not_mutate_active_execution_state():
    text = WORKSTREAM.read_text(encoding="utf-8")

    assert "SET w.status='in_progress'" not in text
    assert "SET w.status='ready'" not in text
    assert "SET w.execution_eligible=true" not in text
    assert "DETACH DELETE" not in text


def test_awareness_projection_is_read_only_and_review_oriented():
    projection = (
        Path(__file__).parents[1]
        / "mycelium"
        / "graph"
        / "control"
        / "read-awareness.cypher"
    ).read_text(encoding="utf-8")

    assert "PriorityProposal" in projection
    assert "GapSignal" in projection
    assert "p.status='proposed'" in projection
    assert "g.mode='shadow'" in projection
    assert "SET " not in projection
    assert "CREATE " not in projection
    assert "DELETE " not in projection


def test_awareness_projection_is_exposed_by_control_and_mcp_surfaces():
    server = (Path(__file__).parents[1] / "control" / "server.py").read_text(encoding="utf-8")
    gateway = (Path(__file__).parents[1] / "control" / "mcp_gateway.py").read_text(encoding="utf-8")

    assert "'read-awareness': {}" in server
    assert "async def read_awareness" in gateway
    assert "call('read-awareness',scope,{})" in gateway
