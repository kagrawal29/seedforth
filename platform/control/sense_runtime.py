"""External process observation only; state reduction and freshness live in graph.

No raw command line, environment, credentials, or model output is stored. Running
means a matching process exists, never that an agent is useful or healthy.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
from uuid import uuid4

from control.graph import Graph

APPROVED_PORTS={'flowing-indian':7745,'cajon-sensei':7724}


def scan_processes():
    result=subprocess.run(['ps','-eo','pid=,args='],capture_output=True,text=True,timeout=10,check=True)
    counts={port:0 for port in APPROVED_PORTS.values()}
    for line in result.stdout.splitlines():
        # Anchored executable + serve avoids matching shells quoting this command.
        match=re.match(r'^\s*\d+\s+(?:\S*/)?opencode\s+serve\s+.*?--port(?:=|\s+)(\d+)(?:\s|$)',line)
        if match and int(match[1]) in counts:
            counts[int(match[1])]+=1
    return counts


def collect(graph,revision):
    sources=graph.query("MATCH (s:SourceStream {adapter:'local-opencode-process-v1',enabled:true}) "
                        "RETURN s.node_id AS id,s.scope_id AS scope,s.port AS port")
    observed_at=datetime.now(timezone.utc).isoformat()
    try:
        counts=scan_processes()
    except (OSError,subprocess.SubprocessError):
        counts=None
    outcomes=[]
    for source in sources:
        if APPROVED_PORTS.get(source['scope'])!=source['port']:
            raise ValueError('unapproved_source_binding')
        count=counts[source['port']] if counts is not None else 0
        status='collection_failed' if counts is None else 'running' if count==1 else 'conflicting' if count>1 else 'stopped'
        payload=dict(source=source['id'],observed_at=observed_at,status=status,process_count=count,revision=revision)
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        rows=graph.operation('record-runtime-observation','principal-runtime-sensor',source['scope'],
            **payload,event_id='obs-'+str(uuid4()),payload_hash=digest)
        if len(rows)!=1:
            raise RuntimeError('observation_not_persisted')
        outcomes.append({'scope':source['scope'],'status':status})
    if not sources:
        raise RuntimeError('no_registered_sources')
    return outcomes


if __name__=='__main__':
    print(json.dumps(collect(Graph(),os.environ['SEEDFORTH_RELEASE_SHA'])))
