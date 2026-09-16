"""Ingest append-only worker action evidence into Mycelium."""
from __future__ import annotations

import json
import os
from pathlib import Path

from control.graph import Graph

STREAM = Path(os.environ.get('SEEDFORTH_DELTA_ACTION_STREAM', '/opt/seedforth/shared/delta-worker-actions.jsonl'))
STATE = Path(os.environ.get('SEEDFORTH_DELTA_ACTION_STATE', '/opt/seedforth/shared/delta-worker-actions-state.json'))
PROCESSOR = 'principal-delta-conversation-processor'


def _cursor(path: Path) -> int:
    try:
        value = json.loads(path.read_text()).get('cursor', 0)
        return value if isinstance(value, int) and value >= 0 else 0
    except (OSError, ValueError, TypeError):
        return 0


def collect_and_dispatch(graph: Graph, stream: Path = STREAM, state: Path = STATE) -> dict[str, int]:
    stats = {'lines': 0, 'dispatched': 0, 'failed': 0}
    if not stream.exists():
        return stats
    cursor = _cursor(state)
    with stream.open(encoding='utf-8') as handle:
        handle.seek(cursor)
        while True:
            raw = handle.readline()
            if not raw:
                break
            stats['lines'] += 1
            try:
                data = json.loads(raw)
                required = ('conversation_message_id','workitem_id','wakeup_id','worker_id','result')
                if (not isinstance(data, dict) or any(not isinstance(data.get(k), str) for k in required)
                        or data.get('action_status') != 'completed'):
                    raise ValueError('invalid_action_evidence')
                rows = graph.operation('record-conversation-action', PROCESSOR, data.get('scope', ''),
                    message_id=data['conversation_message_id'], workitem_id=data['workitem_id'],
                    action_id=data.get('action_id', 'action-' + data['wakeup_id']),
                    wakeup_id=data['wakeup_id'], worker_id=data['worker_id'],
                    action_status=data['action_status'], result=data['result'][:2000])
                if not rows:
                    raise ValueError('action_transition_denied')
                stats['dispatched'] += 1
            except (ValueError, TypeError, json.JSONDecodeError, KeyError):
                stats['failed'] += 1
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(json.dumps({'cursor': handle.tell()}))
    return stats
