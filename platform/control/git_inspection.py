"""Bounded read-only Git adapter; never checks out, pushes, or executes repo code."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from control.broker import InvocationDenied,digest


class GitInspection:
    cost_units=1
    max_seconds=30

    def __init__(self,repositories,artifact_root):
        # These bindings are set by trusted release configuration, not model input.
        self.repositories={scope:Path(path).resolve() for scope,path in repositories.items()}
        self.artifact_root=Path(artifact_root).resolve()
        self.generation=digest({'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'repositories':{k:str(v) for k,v in self.repositories.items()},'artifact_root':str(self.artifact_root)})

    def validate(self,scope,arguments):
        if scope not in self.repositories or not isinstance(arguments,dict) or set(arguments)!={'revision'}:
            raise InvocationDenied('invalid_git_inspection_scope_or_fields')
        revision=arguments['revision']
        if not isinstance(revision,str) or not re.fullmatch('[0-9a-f]{40}',revision):
            raise InvocationDenied('immutable_revision_required')
        return dict(scope=scope,revision=revision)

    def run(self,invocation,arguments):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',invocation):
            raise ValueError('invalid_artifact_identity')
        repository=self.repositories[arguments['scope']]
        command=['git','-c','core.hooksPath=/dev/null','-C',str(repository),'rev-parse','--verify']
        # No inherited provider credentials or executable Git config from HOME.
        env={'PATH':'/usr/bin:/bin','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}
        commit=subprocess.run(command+[arguments['revision']+'^{commit}'],env=env,check=True,
            timeout=10,capture_output=True,text=True).stdout.strip()
        tree=subprocess.run(command+[arguments['revision']+'^{tree}'],env=env,check=True,
            timeout=10,capture_output=True,text=True).stdout.strip()
        if not re.fullmatch('[0-9a-f]{40}',commit) or not re.fullmatch('[0-9a-f]{40}',tree):
            raise ValueError('unsupported_git_object_identity')
        report=dict(kind='git_revision_inspection',scope=arguments['scope'],commit=commit,tree=tree,
            coverage='commit_and_root_tree_identity_only',adapter_generation=self.generation)
        raw=json.dumps(report,sort_keys=True).encode()
        self.artifact_root.mkdir(parents=True,exist_ok=True,mode=0o700)
        target=self.artifact_root/(invocation+'.json')
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return dict(outcome='succeeded',artifact_ref=str(target),artifact_hash=hashlib.sha256(raw).hexdigest())
