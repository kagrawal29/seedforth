"""Ingest Delta acknowledgement observations into Mycelium.

Delta writes only this append-only external stream. Graph reducers decide the
meaning of an acknowledgement; malformed input is quarantined and never
becomes authority.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone
import re

from control.graph import Graph

SHARED = Path(os.environ.get('SEEDFORTH_SHARED_DIR','/opt/seedforth/shared'))
STREAM = Path(os.environ.get('SEEDFORTH_DELTA_ACK_STREAM',str(SHARED/'delta-conversation-acks.jsonl')))
STATE = Path(os.environ.get('SEEDFORTH_DELTA_ACK_STATE',str(SHARED/'delta-conversation-acks-state.json')))
PROCESSOR = 'principal-delta-conversation-processor'


def _read_state(path: Path) -> int:
    try:
        value=json.loads(path.read_text()).get('cursor',0)
        return value if isinstance(value,int) and value>=0 else 0
    except (OSError,ValueError,TypeError):
        return 0


def _write_state(path: Path,cursor: int) -> None:
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps({'cursor':cursor,'updated_at':datetime.now(timezone.utc).isoformat()}))
    os.chmod(temporary,0o600)
    temporary.replace(path)


def _quarantine(path: Path,offset: int,raw: str,reason: str) -> None:
    target=path.with_name(path.name+'.quarantine.jsonl')
    with target.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'offset':offset,'raw':raw[:10000],'reason':reason[:120],
            'quarantined_at':datetime.now(timezone.utc).isoformat()},sort_keys=True)+'\n')
    os.chmod(target,0o600)


def collect_and_dispatch(graph: Graph, stream: Path=STREAM, state: Path=STATE) -> dict[str,int]:
    stats={'lines':0,'dispatched':0,'failed':0}
    if not stream.exists(): return stats
    cursor=_read_state(state)
    if stream.stat().st_size<cursor: cursor=0
    with stream.open('r',encoding='utf-8') as handle:
        handle.seek(cursor)
        while True:
            offset=handle.tell(); raw=handle.readline()
            if not raw or not raw.endswith('\n'): break
            stats['lines']+=1
            try:
                data=json.loads(raw)
                message_id = (data.get('conversation_message_id')
                              if isinstance(data, dict) else None)
                if (not isinstance(data,dict) or not re.fullmatch(r'[a-z0-9-]{1,64}',str(data.get('scope','')))
                        or not isinstance(message_id,str)
                        or not isinstance(data.get('ack_id'),str)
                        or data.get('ack_status') not in {'received','needs_review','rejected'}
                        or not isinstance(data.get('summary'),str)):
                    raise ValueError('invalid_ack')
                rows=graph.operation('record-conversation-ack',PROCESSOR,data['scope'],
                    message_id=message_id,ack_id=data['ack_id'],
                    ack_status=data['ack_status'],summary=data['summary'][:2000])
                if not rows: raise ValueError('ack_transition_denied')
                stats['dispatched']+=1
            except (ValueError,TypeError,json.JSONDecodeError) as exc:
                _quarantine(stream,offset,raw,str(exc)); stats['failed']+=1
            _write_state(state,handle.tell())
    return stats


if __name__=='__main__':
    print(json.dumps(collect_and_dispatch(Graph()),sort_keys=True))
