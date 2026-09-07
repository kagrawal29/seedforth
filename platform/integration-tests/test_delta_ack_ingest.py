import json

from control.ingest_delta_acks import collect_and_dispatch


class Graph:
    def __init__(self): self.calls=[]
    def operation(self,name,actor,scope,**params):
        self.calls.append((name,actor,scope,params))
        return [{'message_id':params['message_id']}]


def test_ack_ingest_dispatches_and_quarantines(tmp_path):
    stream=tmp_path/'acks.jsonl'; state=tmp_path/'state.json'
    stream.write_text('\n'.join([
        json.dumps({'scope':'cajon-sensei','conversation_message_id':'message-a','ack_id':'ack-12345678',
                    'ack_status':'received','summary':'received as content'}),
        '{not-json}',
        json.dumps({'scope':'cajon-sensei','conversation_message_id':'message-b','ack_id':'ack-87654321',
                    'ack_status':'approved','summary':'invalid status'}),
    ])+'\n')
    graph=Graph(); result=collect_and_dispatch(graph,stream,state)
    assert result=={'lines':3,'dispatched':1,'failed':2}
    assert graph.calls[0][0]=='record-conversation-ack'
    assert (tmp_path/'acks.jsonl.quarantine.jsonl').exists()
    assert json.loads(state.read_text())['cursor']==stream.stat().st_size
