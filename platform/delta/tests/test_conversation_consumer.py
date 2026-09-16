import json

from delta.conversation_consumer import consume_once
from delta.mycelium_ack import validate_ack
from delta.worker_evidence import append_action


def test_consumer_ack_is_after_bound_wakeup_and_action_is_separate(tmp_path):
    inbox = tmp_path / 'inbox'; inbox.mkdir()
    payload = {
        'id': 'seedforth-message-abc',
        'source': 'mycelium-conversation-processor',
        'scope': 'cajon-sensei',
        'originator': 'principal-human',
        'conversation_message_id': 'message-abc',
        'conversation_request_hash': 'request-hash',
        'workitem_id': 'wi-cajon-1',
        'text': 'untrusted direction',
        'trust': 'authenticated_origin_untrusted_content',
    }
    (inbox / 'message-abc.json').write_text(json.dumps(payload))
    acks = tmp_path / 'acks.jsonl'
    actions = tmp_path / 'actions.jsonl'
    wake_marker = tmp_path / '.nudge'

    def wake(worker_payload):
        assert worker_payload['workitem_id'] == 'wi-cajon-1'
        wake_marker.touch()
        wakeup = 'wakeup-message-abc'
        append_action(actions, scope='cajon-sensei',
                      message_id=worker_payload['conversation_message_id'],
                      workitem_id=worker_payload['workitem_id'],
                      wakeup_id=wakeup, worker_id='worker-cajon-1',
                      result='bounded fixture worker processed the direction')
        return {'wakeup_id': wakeup, 'worker_id': 'worker-cajon-1'}

    result = consume_once(inbox, acks, 'cajon-sensei', wake)
    assert result == {'seen': 1, 'consumed': 1, 'rejected': 0, 'wake_failed': 0}
    assert wake_marker.exists()
    assert not (inbox / 'message-abc.json').exists()
    ack = json.loads(acks.read_text())
    assert ack['ack_status'] == 'received'
    action = json.loads(actions.read_text())
    assert action['workitem_id'] == 'wi-cajon-1'
    assert action['action_status'] == 'completed'


def test_failed_wakeup_does_not_ack_or_consume(tmp_path):
    inbox = tmp_path / 'inbox'; inbox.mkdir()
    payload = {
        'id': 'seedforth-message-xyz', 'source': 'mycelium-conversation-processor',
        'scope': 'cajon-sensei', 'conversation_message_id': 'message-xyz',
        'conversation_request_hash': 'request-hash', 'workitem_id': 'wi-cajon-2',
        'text': 'direction', 'trust': 'authenticated_origin_untrusted_content',
    }
    path = inbox / 'message-xyz.json'; path.write_text(json.dumps(payload))
    result = consume_once(inbox, tmp_path / 'acks.jsonl', 'cajon-sensei',
                          lambda _: (_ for _ in ()).throw(RuntimeError('worker_down')))
    assert result == {'seen': 1, 'consumed': 0, 'rejected': 0, 'wake_failed': 1}
    assert path.exists()
    assert not (tmp_path / 'acks.jsonl').exists()
