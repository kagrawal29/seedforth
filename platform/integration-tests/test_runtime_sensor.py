from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from control import sense_runtime


def test_only_exact_process_executables_and_ports_count(monkeypatch):
    output=''' 10 /usr/bin/opencode serve --port 7745
 11 opencode serve --port=7724
 12 bash -c opencode serve --port 7745
 13 opencode serve --port 77450
 14 echo opencode serve --port 7724
'''
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=output))
    assert sense_runtime.scan_processes()=={7745:1,7724:1}


def test_collect_does_not_mark_scan_failure_as_stopped(monkeypatch):
    def fail():
        raise subprocess.TimeoutExpired('ps',10)
    monkeypatch.setattr(sense_runtime,'scan_processes',fail)
    class Graph:
        def query(self,*a):
            return [dict(id='source-runtime-flowing-indian',scope='flowing-indian',port=7745)]
        def operation(self,*a,**params):
            assert params['status']=='collection_failed'
            assert 'stdout' not in params
            return [dict(id='observed')]
    assert sense_runtime.collect(Graph(),'fixture')[0]['status']=='collection_failed'
