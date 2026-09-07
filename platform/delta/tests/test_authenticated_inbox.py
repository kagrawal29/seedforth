import json

from delta.project_bridge import ProjectBridge


def test_authenticated_inbox_only_accepts_mycelium_source(tmp_path, monkeypatch):
    bridge = ProjectBridge(name="hub", data_dir=str(tmp_path), serve_port=7700)
    accepted = []
    bridge.deliver_message = lambda *args, **kwargs: accepted.append((args, kwargs))
    (bridge.inbox_dir / "ordinary.json").write_text(json.dumps({
        "id": "ordinary", "channel": "c", "user": "u", "text": "ordinary"
    }))
    (bridge.inbox_dir / "mycelium.json").write_text(json.dumps({
        "id": "mycelium-1", "channel": "mycelium:cajon-sensei",
        "user": "mycelium:principal", "text": "untrusted",
        "source": "mycelium-conversation-processor"
    }))

    calls = 0
    original_wait = bridge._shutdown_event.wait

    def stop_after_one(_timeout):
        nonlocal calls
        calls += 1
        if calls >= 1:
            bridge._shutdown_event.set()
        original_wait(0.001)

    monkeypatch.setattr(bridge._shutdown_event, "wait", stop_after_one)
    bridge.watch_authenticated_inbox(lambda data: None, poll_interval=1)

    assert len(accepted) == 1
    assert accepted[0][0][0] == "mycelium:cajon-sensei"
    assert accepted[0][0][2].startswith("[TRANSPORT PROTOCOL]")
