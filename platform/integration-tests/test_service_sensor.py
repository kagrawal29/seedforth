from control.sense_services import show_unit, collect


def test_show_unit_uses_allowlisted_systemctl_and_parses_status():
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        class Result:
            stdout = ("ActiveState=inactive\nSubState=dead\nResult=success\n"
                      "ExecMainStatus=0\nExecMainExitTimestamp=Mon 2026-09-07 13:00:00 UTC\n")
        return Result()

    value = show_unit("seedforth-code-sensor.service", runner)
    assert value["Result"] == "success"
    assert value["ExecMainStatus"] == "0"
    assert calls[0][0][:3] == ["/usr/bin/systemctl", "show", "seedforth-code-sensor.service"]
    assert calls[0][1]["check"] is True


def test_show_unit_rejects_unapproved_path():
    try:
        show_unit("../secret.service", lambda *args, **kwargs: None)
    except ValueError as exc:
        assert str(exc) == "unapproved_unit"
    else:
        raise AssertionError("path traversal accepted")


class FakeGraph:
    def __init__(self):
        self.calls = []

    def query(self, statement, params):
        assert params["adapter"] == "systemd-unit-health-v1"
        return [{"id": "source-service-seedforth-code-sensor",
                 "unit": "seedforth-code-sensor.service"}]

    def operation(self, name, actor, scope, **params):
        self.calls.append((name, actor, scope, params))
        assert name == "record-service-observation"
        return [{"status": params["status"]}]


def test_collect_records_success_without_storing_raw_systemd_output():
    graph = FakeGraph()

    def runner(args, **kwargs):
        class Result:
            stdout = ("ActiveState=inactive\nSubState=dead\nResult=success\n"
                      "ExecMainStatus=0\nExecMainExitTimestamp=timestamp\n")
        return Result()

    assert collect(graph, "a" * 40, runner) == [{"unit": "seedforth-code-sensor.service", "status": "success"}]
    payload = graph.calls[0][3]
    assert "raw" not in payload
    assert payload["exec_main_status"] == "0"
