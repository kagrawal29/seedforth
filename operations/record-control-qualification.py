"""Admit an actual pytest JUnit result as release evidence, not product progress."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'platform'))
from control.graph import Graph


def record(revision,junit):
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896' or not re.fullmatch('[0-9a-f]{40}',revision):
        raise RuntimeError('invalid_qualification_target')
    source=Path(junit).resolve()
    if not source.is_relative_to('/tmp/seedforth-upgrade.Eb1GkXTC') or source.stat().st_size>2_000_000:
        raise RuntimeError('invalid_qualification_artifact')
    raw=source.read_bytes()
    root=ET.fromstring(raw)
    cases=list(root.iter('testcase'))
    if not cases or any(list(root.iter(name)) for name in ['failure','error','skipped']):
        raise RuntimeError('qualification_not_fully_passed')
    digest=hashlib.sha256(raw).hexdigest()
    target=Path('/opt/seedforth/shared/backups')/('qualification-'+revision[:7]+'-'+digest[:12]+'.xml')
    if target.exists():
        if target.read_bytes()!=raw:
            raise RuntimeError('qualification_artifact_collision')
    else:
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    rows=Graph().query("MERGE (r:TestRun:ReleaseQualification {node_id:$id}) "
        "ON CREATE SET r.scope_id='seedforth-platform',r.project='mycelium',"
        "r.status='passed',r.runner='delta2-pytest',r.source_revision=$revision,"
        "r.artifact_ref=$artifact,r.artifact_hash=$hash,r.tests_passed=$count,"
        "r.evidence_kind='release_qualification',r.finished_at=datetime($finished),r.recorded_at=datetime() "
        "WITH r MATCH (w:WorkItem {node_id:'wi-upgrade-W21',scope_id:'seedforth-platform'}) "
        "MERGE (r)-[:INFORMS]->(w) RETURN r.node_id AS id,r.tests_passed AS passed",
        dict(id='qualification:'+revision+':'+digest,revision=revision,artifact=str(target),
             hash=digest,count=len(cases),finished=datetime.fromtimestamp(source.stat().st_mtime,timezone.utc).isoformat()))
    if len(rows)!=1:
        raise RuntimeError('qualification_plan_link_missing')
    print(json.dumps(rows[0]))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    parser.add_argument('--junit',required=True)
    args=parser.parse_args()
    record(args.revision,args.junit)
