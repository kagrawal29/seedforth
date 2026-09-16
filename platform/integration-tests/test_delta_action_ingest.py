import json

from control.ingest_delta_actions import collect_and_dispatch


class Graph:
    def __init__(self): self.calls = []
    def operation(self, name, actor, scope, **params):
        self.calls.append((name, actor, scope, params))
        return [{'action_id': params['action_id'], 'execution_state': 'action_evidenced'}]


def test_action_ingest_dispatches_only_completed_bound_evidence(tmp_path):
    stream = tmp_path / 'actions.jsonl'
    stream.write_text(json.dumps({
        'scope': 'cajon-sensei', 'conversation_message_id': 'message-a',
        'workitem_id': 'wi-a', 'wakeup_id': 'wake-a', 'worker_id': 'worker-a',
        'action_status': 'completed', 'result': 'fixture action',
    }) + '\n' + json.dumps({
        'scope': 'cajon-sensei', 'conversation_message_id': 'message-b',
        'workitem_id': 'wi-b', 'wakeup_id': 'wake-b', 'worker_id': 'worker-b',
        'action_status': 'started', 'result': 'not completion evidence',
    }) + '\n')
    graph = Graph()
    result = collect_and_dispatch(graph, stream, tmp_path / 'state.json')
    assert result == {'lines': 2, 'dispatched': 1, 'failed': 1}
    assert graph.calls[0][0] == 'record-conversation-action'
    assert graph.calls[0][2] == 'cajon-sensei'
