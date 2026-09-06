from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.isolated_worker import execute

JOB={'scope':'fixture','work':'work','attempt':'attempt','invocation':'invocation'}


def test_worker_uses_graph_spec_and_stops_at_review():
    calls=[]
    def call(name,**params):
        calls.append((name,params))
        return {'read-attempt':[], 'read-work':[{'id':'work','status':'ready','hold':False,'version':7}],
            'claim-work':[{'fence':3}], 'read-execution-spec':[{'capability':'approved','arguments_json':'{"key":"data"}'}],
            'invoke':[{'status':'succeeded'}], 'complete-invocation-work':[{'status':'review','receipt':'receipt'}]}[name]
    assert execute(JOB,call)['accepted'] is False
    assert calls[2][1]['version']==7
    assert calls[4][1]['capability']=='approved' and calls[4][1]['arguments']=={'key':'data'}
    assert calls[-1][0]=='complete-invocation-work'


def test_existing_attempt_never_restarts():
    calls=[]
    def call(name,**params):
        calls.append(name)
        return [{'status':'unknown'}]
    with pytest.raises(RuntimeError): execute(JOB,call)
    assert calls==['read-attempt']


def test_job_cannot_supply_commands():
    with pytest.raises(ValueError): execute({**JOB,'command':'anything'},None)
